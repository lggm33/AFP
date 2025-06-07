from datetime import datetime, timedelta, UTC
from typing import Optional

from .base_worker import BaseWorker
from ..models.email_import_job import EmailImportJob
from ..models.email_parsing_job import EmailParsingJob
from ..models.job_queue import JobQueue
from ..infrastructure.email.gmail_client import GmailAPIClient
from ..core.database import db


class EmailImportWorker(BaseWorker):
    """
    Worker that processes email import jobs.
    
    Continuously processes JobQueue entries for 'email_import':
    1. Takes job from queue
    2. Uses Gmail API to fetch new emails
    3. Creates EmailParsingJob for each email
    4. Updates EmailImportJob statistics
    """
    
    def __init__(self):
        super().__init__(name="EmailImport", sleep_interval=2.0)
    
    def _ensure_utc_timezone(self, dt: Optional[datetime]) -> Optional[datetime]:
        """Ensure datetime has UTC timezone"""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt
    
    def _determine_smart_search_date(self, gmail_client: 'GmailAPIClient', email_job: EmailImportJob) -> datetime:
        """
        Determine smart search date using the following logic:
        1. First try to get last processed email date from AFP labels
        2. If no processed emails, use integration's custom lookback or default to 30 days
        3. Never go beyond 30 days unless explicitly configured
        """
        integration = email_job.integration
        
        # Try to get date of last processed email from Gmail labels
        try:
            last_processed_date = gmail_client.get_last_processed_email_date()
            if last_processed_date:
                self.logger.info(f"📧 Found last processed email date: {last_processed_date}")
                return last_processed_date
        except Exception as e:
            self.logger.warning(f"⚠️ Could not get last processed email date: {str(e)}")
        
        # Fallback: Check if integration has custom lookback configuration
        # We could add a field like `initial_lookback_days` to Integration model
        default_lookback_days = 30  # Changed from 7 to 30 days
        
        # Check if integration has custom lookback (future enhancement)
        if hasattr(integration, 'initial_lookback_days') and integration.initial_lookback_days:
            lookback_days = min(integration.initial_lookback_days, 30)  # Cap at 30 days
            self.logger.info(f"🔧 Using custom lookback: {lookback_days} days")
        else:
            lookback_days = default_lookback_days
            self.logger.info(f"🔧 Using default lookback: {lookback_days} days")
        
        fallback_date = datetime.now(UTC) - timedelta(days=lookback_days)
        self.logger.info(f"📅 No processed emails found, searching {lookback_days} days back")
        
        return fallback_date
    
    def process_cycle(self):
        """Process one email import job from the queue"""
        try:
            # Get next job from queue
            queue_job = db.session.query(JobQueue).filter_by(
                queue_name='email_import',
                status='pending'
            ).order_by(JobQueue.priority.desc(), JobQueue.created_at.asc()).first()
            
            if not queue_job:
                return  # No jobs to process
            
            # Get associated EmailImportJob
            email_job_id = queue_job.job_data.get('email_import_job_id')
            if not email_job_id:
                self.logger.error(f"Invalid job data in queue job {queue_job.id}")
                queue_job.status = 'failed'
                queue_job.error_message = 'Invalid job data'
                db.session.commit()
                return
            
            email_job = db.session.query(EmailImportJob).get(email_job_id)
            if not email_job:
                self.logger.error(f"EmailImportJob {email_job_id} not found")
                queue_job.status = 'failed'
                queue_job.error_message = 'EmailImportJob not found'
                db.session.commit()
                return
            
            # Mark jobs as running
            queue_job.status = 'running'
            queue_job.worker_id = self.worker_id
            queue_job.started_at = datetime.now(UTC)
            
            email_job.status = 'running'
            email_job.worker_id = self.worker_id
            email_job.started_at = datetime.now(UTC)
            email_job.timeout_at = datetime.now(UTC) + timedelta(minutes=30)  # 30 min timeout
            
            db.session.commit()
            
            self.logger.info(f"Processing EmailImportJob {email_job.id} for Integration {email_job.integration_id}")
            
            # Process the job
            try:
                result = self._process_email_import(email_job)
                
                # Update job status - set back to pending and schedule next run
                current_time = datetime.now(UTC)
                email_job.status = 'pending'
                email_job.completed_at = current_time
                email_job.last_run_at = current_time
                email_job.total_runs += 1
                email_job.emails_found_last_run = result['emails_found']
                email_job.emails_processed_last_run = result['emails_processed']
                email_job.total_emails_processed += result['emails_processed']
                email_job.consecutive_errors = 0
                email_job.error_message = None
                
                # Schedule next run based on integration sync frequency
                email_job.next_run_at = current_time + timedelta(
                    minutes=email_job.integration.sync_frequency_minutes
                )
                
                # Calculate duration (handle timezone-aware/naive datetime)
                current_time = datetime.now(UTC)
                start_time = self._ensure_utc_timezone(email_job.started_at)
                duration_seconds = (current_time - start_time).total_seconds()
                email_job.last_run_duration_seconds = int(duration_seconds)
                
                # Add to run history
                run_record = {
                    'timestamp': datetime.now(UTC).isoformat(),
                    'emails_found': result['emails_found'],
                    'emails_processed': result['emails_processed'],
                    'duration_seconds': duration_seconds,
                    'worker_id': self.worker_id
                }
                
                # Initialize run_history if None
                if email_job.run_history is None:
                    email_job.run_history = []
                
                email_job.run_history.append(run_record)
                
                # Keep only last 50 runs
                if len(email_job.run_history) > 50:
                    email_job.run_history = email_job.run_history[-50:]
                
                # Mark queue job as completed
                queue_job.status = 'completed'
                queue_job.completed_at = datetime.now(UTC)
                
                self.logger.info(
                    f"Completed EmailImportJob {email_job.id}: "
                    f"{result['emails_found']} emails found, "
                    f"{result['emails_processed']} processed in {duration_seconds:.1f}s, "
                    f"next run at {email_job.next_run_at}"
                )
                
            except Exception as e:
                # Handle job failure - mark as failed but schedule retry with exponential backoff
                current_time = datetime.now(UTC)
                email_job.status = 'failed'
                email_job.completed_at = current_time
                email_job.consecutive_errors += 1
                email_job.error_message = str(e)
                
                # Exponential backoff: 2^consecutive_errors * base_frequency (capped at 120 min)
                base_minutes = email_job.integration.sync_frequency_minutes
                backoff_multiplier = 2 ** email_job.consecutive_errors
                retry_delay_minutes = min(base_minutes * backoff_multiplier, 120)
                email_job.next_run_at = current_time + timedelta(minutes=retry_delay_minutes)
                
                queue_job.status = 'failed'
                queue_job.error_message = str(e)
                queue_job.completed_at = current_time
                
                self.logger.error(
                    f"Failed to process EmailImportJob {email_job.id}: {str(e)}, "
                    f"will retry at {email_job.next_run_at} (exponential backoff: {retry_delay_minutes}m, "
                    f"consecutive errors: {email_job.consecutive_errors})"
                )
            
            finally:
                email_job.worker_id = None
                queue_job.worker_id = None
                db.session.commit()
                
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error in email import cycle: {str(e)}")
            raise
    
    def _process_email_import(self, email_job: EmailImportJob) -> dict:
        """Process a single email import job"""
        integration = email_job.integration
        
        # Initialize Gmail client
        gmail_client = GmailAPIClient()
        
        # NEW LOGIC: Use intelligent date determination based on AFP labels
        since_date = self._determine_smart_search_date(gmail_client, email_job)
        
        self.logger.info(f"Searching for emails since: {since_date}")
        
        # Fetch new emails
        emails = gmail_client.get_bank_emails(since_date=since_date, max_results=50)
        
        emails_processed = 0
        
        for email_data in emails:
            try:
                # Check if email already exists  
                email_message_id = email_data.get('message_id') or email_data.get('gmail_id')
                existing_parsing_job = db.session.query(EmailParsingJob).filter_by(
                    email_message_id=email_message_id
                ).first()
                
                if existing_parsing_job:
                    self.logger.debug(f"Email {email_message_id} already exists, skipping")
                    continue
                
                # Create EmailParsingJob
                parsing_job = EmailParsingJob(
                    email_import_job_id=email_job.id,
                    email_message_id=email_message_id,
                    email_body=email_data.get('body', ''),
                    email_from=email_data.get('from', ''),
                    email_subject=email_data.get('subject', ''),
                    status='waiting',
                    created_at=datetime.now(UTC)
                )
                
                db.session.add(parsing_job)
                emails_processed += 1
                
                self.logger.debug(f"Created EmailParsingJob for email {email_message_id}")
                
            except Exception as e:
                self.logger.error(f"Error processing email {email_data.get('message_id', 'unknown')}: {str(e)}")
                continue
        
        return {
            'emails_found': len(emails),
            'emails_processed': emails_processed
        }
    
    def reset_worker_jobs(self):
        """Reset jobs that were being processed by this worker"""
        try:
            # Reset EmailImportJobs
            stuck_email_jobs = db.session.query(EmailImportJob).filter_by(
                worker_id=self.worker_id,
                status='running'
            ).all()
            
            for job in stuck_email_jobs:
                job.status = 'failed'
                job.error_message = 'Worker stopped unexpectedly'
                job.worker_id = None
                job.consecutive_errors += 1
                self.logger.info(f"Reset stuck EmailImportJob {job.id}")
            
            # Reset JobQueue entries
            stuck_queue_jobs = db.session.query(JobQueue).filter_by(
                worker_id=self.worker_id,
                status='running',
                queue_name='email_import'
            ).all()
            
            for job in stuck_queue_jobs:
                job.status = 'failed'
                job.error_message = 'Worker stopped unexpectedly'
                job.worker_id = None
                self.logger.info(f"Reset stuck JobQueue entry {job.id}")
                
        except Exception as e:
            self.logger.error(f"Error resetting worker jobs: {str(e)}") 