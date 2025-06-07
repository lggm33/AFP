from datetime import datetime, UTC
from sqlalchemy import func, String

from .base_worker import BaseWorker
from ..models.email_parsing_job import EmailParsingJob
from ..models.job_queue import JobQueue
from ..core.database import db


class ParsingDetectorWorker(BaseWorker):
    """
    Worker that detects EmailParsingJobs ready for processing.
    
    Runs every 15 seconds and:
    1. Finds EmailParsingJobs with status='pending'
    2. Creates JobQueue entries for email_parsing
    3. Updates status to 'queued'
    """
    
    def __init__(self):
        super().__init__(name="ParsingDetector", sleep_interval=15.0)
    
    def process_cycle(self):
        """Process one cycle of parsing job detection"""
        try:
            # Find EmailParsingJobs ready for processing
            pending_jobs = db.session.query(EmailParsingJob).filter_by(
                parsing_status='pending'
            ).limit(100).all()  # Process in batches to avoid overwhelming
            
            if not pending_jobs:
                self.logger.debug("No parsing jobs ready for processing")
                return
            
            jobs_queued = 0
            
            for parsing_job in pending_jobs:
                try:
                    # Check if job is already queued to avoid duplicates
                    existing_queue_job = db.session.query(JobQueue).filter_by(
                        queue_name='email_parsing',
                        status='pending'
                    ).filter(
                        func.cast(JobQueue.job_data['email_parsing_job_id'], String) == str(parsing_job.id)
                    ).first()
                    
                    if existing_queue_job:
                        self.logger.debug(f"ParsingJob {parsing_job.id} already queued, skipping")
                        continue
                    
                    # Create JobQueue entry
                    queue_job = JobQueue(
                        queue_name='email_parsing',
                        job_type='email_parsing',
                        job_data={'email_parsing_job_id': parsing_job.id},
                        status='pending',
                        priority=1,
                        created_at=datetime.now(UTC)
                    )
                    db.session.add(queue_job)
                    
                    # Update EmailParsingJob status
                    parsing_job.parsing_status = 'queued'
                    
                    jobs_queued += 1
                    
                    self.logger.debug(f"Queued EmailParsingJob {parsing_job.id} for processing")
                    
                except Exception as e:
                    self.logger.error(f"Error processing EmailParsingJob {parsing_job.id}: {str(e)}")
                    continue
            
            if jobs_queued > 0:
                db.session.commit()
                self.logger.info(f"Successfully queued {jobs_queued} email parsing jobs")
            else:
                self.logger.debug("No new parsing jobs queued")
                
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error in parsing detection cycle: {str(e)}")
            raise
    
    def reset_worker_jobs(self):
        """Reset any jobs that might be stuck in queued state"""
        try:
            # Reset EmailParsingJobs that were queued but never picked up
            stuck_jobs = db.session.query(EmailParsingJob).filter_by(
                parsing_status='queued'
            ).all()
            
            for job in stuck_jobs:
                # Check if they have a corresponding queue entry
                queue_job = db.session.query(JobQueue).filter_by(
                    queue_name='email_parsing',
                    status='pending'
                ).filter(
                    func.cast(JobQueue.job_data['email_parsing_job_id'], String) == str(job.id)
                ).first()
                
                if not queue_job:
                    # No queue entry, reset to pending
                    job.parsing_status = 'pending'
                    self.logger.info(f"Reset stuck EmailParsingJob {job.id} to pending")
            
        except Exception as e:
            self.logger.error(f"Error resetting worker jobs: {str(e)}") 