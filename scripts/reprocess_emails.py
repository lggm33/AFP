#!/usr/bin/env python3
"""
Script to reset email parsing jobs back to waiting status
so they can be reprocessed with the new bank identification logic.
"""

import sys
sys.path.insert(0, '.')

from app.core.database import init_database, db
from app.models.email_parsing_job import EmailParsingJob
from datetime import datetime, UTC

def reset_emails_for_reprocessing(limit: int = 10):
    """Reset email parsing jobs to waiting status for reprocessing"""
    print(f"🔄 RESETTING {limit} EMAIL PARSING JOBS FOR REPROCESSING")
    print("=" * 80)
    
    init_database()
    
    try:
        # Get completed jobs with no bank_id assigned
        jobs_to_reset = db.session.query(EmailParsingJob).filter(
            EmailParsingJob.bank_id.is_(None),
            EmailParsingJob.status.in_(['completed', 'error'])
        ).limit(limit).all()
        
        if not jobs_to_reset:
            print("❌ No email parsing jobs found to reset")
            return
        
        print(f"Found {len(jobs_to_reset)} jobs to reset")
        
        reset_count = 0
        for job in jobs_to_reset:
            # Reset job to waiting status
            job.status = 'waiting'
            job.summary = None
            job.worker_id = None
            job.started_at = None
            job.completed_at = None
            job.error_message = None
            job.parsing_attempts = 0
            job.confidence_score = 0.0
            job.extracted_data = None
            job.parsing_rules_used = None
            
            reset_count += 1
            print(f"✅ Reset EmailParsingJob {job.id} (from: {job.email_from[:50]}...)")
        
        db.session.commit()
        
        print(f"\n🎯 SUCCESSFULLY RESET {reset_count} JOBS")
        print("   These jobs will be picked up by ParsingDetectorWorker")
        print("   and processed by TransactionCreationWorker with bank identification")
        
    except Exception as e:
        print(f"❌ Error resetting jobs: {e}")
        db.session.rollback()

if __name__ == "__main__":
    reset_emails_for_reprocessing(limit=5) 