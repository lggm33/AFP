#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from app.core.database import init_database, db
from app.models.email_import_job import EmailImportJob
from app.models.integration import Integration
from datetime import datetime, UTC

def main():
    init_database()
    
    print("🔍 CHECKING EMAIL IMPORT JOB STATUS")
    print("="*50)
    
    # Get the job
    job = db.session.query(EmailImportJob).first()
    
    if not job:
        print("❌ No EmailImportJob found")
        return
    
    # Get integration
    integration = db.session.query(Integration).filter_by(id=job.integration_id).first()
    
    current_time = datetime.now(UTC)
    
    print(f"📧 Job ID: {job.id}")
    print(f"📧 Status: {job.status}")
    print(f"📧 Integration ID: {job.integration_id}")
    print(f"📧 Integration Active: {integration.is_active if integration else 'N/A'}")
    print(f"📧 Next run at: {job.next_run_at}")
    print(f"🕐 Current time: {current_time}")
    
    if job.next_run_at:
        # Handle timezone aware/naive datetime comparison
        if job.next_run_at.tzinfo is None:
            next_run_utc = job.next_run_at.replace(tzinfo=UTC)
        else:
            next_run_utc = job.next_run_at
            
        time_diff = (current_time - next_run_utc).total_seconds()
        print(f"⏰ Time difference: {time_diff:.1f} seconds")
        print(f"✅ Ready to run: {'YES' if next_run_utc <= current_time else 'NO'}")
    else:
        print("⚠️ No next_run_at time set")
    
    print(f"🔄 Last run at: {job.last_run_at}")
    print(f"📊 Total runs: {job.total_runs}")
    print(f"❌ Consecutive errors: {job.consecutive_errors}")
    
    # Check if integration has tokens
    if integration:
        has_tokens = bool(integration.access_token and integration.refresh_token)
        print(f"🔑 Has OAuth tokens: {'YES' if has_tokens else 'NO'}")
    
    print("="*50)

if __name__ == "__main__":
    main() 