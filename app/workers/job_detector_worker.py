from datetime import datetime, timedelta, UTC
from sqlalchemy import and_, func, String

from .base_worker import BaseWorker
from ..models.integration import Integration
from ..models.email_import_job import EmailImportJob
from ..models.job_queue import JobQueue
from ..core.database import db


class JobDetectorWorker(BaseWorker):
    """
    Worker that detects EmailImportJobs ready for execution.
    
    Runs every 30 seconds and:
    1. Finds EmailImportJobs with next_run_at <= now
    2. Creates JobQueue entries for email_import
    3. Updates next_run_at based on sync_frequency
    """
    
    def __init__(self):
        super().__init__(name="JobDetector", sleep_interval=30.0)
    
    def process_cycle(self):
        """Process one cycle of job detection"""
        try:
            # Find EmailImportJobs ready to run (includes failed jobs ready for retry)
            ready_jobs = db.session.query(EmailImportJob)\
                .join(Integration)\
                .filter(
                    and_(
                        EmailImportJob.next_run_at <= datetime.now(UTC),
                        Integration.is_active == True,
                        EmailImportJob.status.in_(['completed', 'failed', 'idle', 'ready', 'pending'])
                    )
                ).all()
            
            if not ready_jobs:
                self.logger.debug("No jobs ready for execution")
                return
            
            jobs_queued = 0
            
            for email_job in ready_jobs:
                try:
                    # Check if job is already queued to avoid duplicates
                    existing_queue_job = db.session.query(JobQueue).filter_by(
                        queue_name='email_import',
                        status='pending'
                    ).filter(
                        func.cast(JobQueue.job_data['email_import_job_id'], String) == str(email_job.id)
                    ).first()
                    
                    if existing_queue_job:
                        self.logger.debug(f"Job {email_job.id} already queued, skipping")
                        continue
                    
                    # Create JobQueue entry
                    queue_job = JobQueue(
                        queue_name='email_import',
                        job_type='email_import',
                        job_data={'email_import_job_id': email_job.id},
                        status='pending',
                        priority=1,
                        created_at=datetime.now(UTC)
                    )
                    db.session.add(queue_job)
                    
                    # Check if this is a retry after failure
                    is_retry = email_job.status == 'failed'
                    retry_info = f" (RETRY #{email_job.consecutive_errors})" if is_retry else ""
                    
                    # Update EmailImportJob status
                    email_job.status = 'queued'
                    email_job.worker_id = None
                    
                    # Schedule next run based on sync frequency (only for successful jobs)
                    if not is_retry:
                        email_job.next_run_at = datetime.now(UTC) + timedelta(
                            minutes=email_job.integration.sync_frequency_minutes
                        )
                    
                    jobs_queued += 1
                    
                    self.logger.info(
                        f"Queued EmailImportJob {email_job.id} for Integration {email_job.integration_id}{retry_info} "
                        f"(next run: {email_job.next_run_at})"
                    )
                    
                except Exception as e:
                    self.logger.error(f"Error processing EmailImportJob {email_job.id}: {str(e)}")
                    continue
            
            if jobs_queued > 0:
                db.session.commit()
                self.logger.info(f"Successfully queued {jobs_queued} email import jobs")
            else:
                self.logger.debug("No new jobs queued")
                
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error in job detection cycle: {str(e)}")
            raise
    
    def reset_worker_jobs(self):
        """Reset any jobs that might be stuck in queued state"""
        try:
            # Reset EmailImportJobs that were queued but never picked up
            stuck_jobs = db.session.query(EmailImportJob).filter_by(
                status='queued',
                worker_id=None
            ).all()
            
            for job in stuck_jobs:
                # Check if they have a corresponding queue entry
                queue_job = db.session.query(JobQueue).filter_by(
                    queue_name='email_import',
                    status='pending'
                ).filter(
                    func.cast(JobQueue.job_data['email_import_job_id'], String) == str(job.id)
                ).first()
                
                if not queue_job:
                    # No queue entry, reset to idle
                    job.status = 'idle'
                    self.logger.info(f"Reset stuck EmailImportJob {job.id} to idle")
            
        except Exception as e:
            self.logger.error(f"Error resetting worker jobs: {str(e)}") 