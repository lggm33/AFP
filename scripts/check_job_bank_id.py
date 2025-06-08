#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import DatabaseSession
from app.models.email_parsing_job import EmailParsingJob

with DatabaseSession() as db:
    job = db.query(EmailParsingJob).get(19)
    print(f'Job 19 bank_id: {job.bank_id}')
    
    # Check all recent jobs
    jobs = db.query(EmailParsingJob).order_by(EmailParsingJob.id.desc()).limit(5).all()
    print('\nRecent jobs:')
    for j in jobs:
        print(f'  Job {j.id}: bank_id={j.bank_id}') 