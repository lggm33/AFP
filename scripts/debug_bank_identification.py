#!/usr/bin/env python3
"""
Debug script to investigate bank identification issues
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import DatabaseSession
from app.models.email_parsing_job import EmailParsingJob
from app.models.bank import Bank

def main():
    print("🔍 DEBUGGING BANK IDENTIFICATION")
    print("=" * 60)
    
    with DatabaseSession() as db:
        # Get recent parsing jobs
        jobs = db.query(EmailParsingJob).order_by(EmailParsingJob.id.desc()).limit(5).all()
        
        print("📧 RECENT EMAIL PARSING JOBS:")
        print("-" * 60)
        for job in jobs:
            print(f"Job ID: {job.id}")
            print(f"  Bank ID: {job.bank_id}")
            print(f"  From: {job.email_from}")
            print(f"  Subject: {job.email_subject[:50]}...")
            print()
        
        print("\n🏦 CONFIGURED BANKS:")
        print("-" * 60)
        banks = db.query(Bank).filter_by(is_active=True).all()
        for bank in banks:
            print(f"{bank.name} (ID: {bank.id})")
            print(f"  sender_emails: {bank.sender_emails}")
            print(f"  sender_domains: {bank.sender_domains}")
            print()
        
        # Test identification for Scotiabank email
        scotia_jobs = [j for j in jobs if 'AlertasScotiabank' in j.email_from]
        if scotia_jobs:
            test_job = scotia_jobs[0]
            print(f"\n🧪 TESTING SCOTIABANK EMAIL (JOB {test_job.id}):")
            print("-" * 60)
            print(f"Email from: {test_job.email_from}")
            test_identification(test_job, banks)
        
        # Test identification for BAC email
        bac_jobs = [j for j in jobs if 'notificacionesbaccr' in j.email_from]
        if bac_jobs:
            test_job = bac_jobs[0]
            print(f"\n🧪 TESTING BAC EMAIL (JOB {test_job.id}):")
            print("-" * 60)
            print(f"Email from: {test_job.email_from}")
            test_identification(test_job, banks)

def test_identification(test_job, banks):
    """Test bank identification for a specific job"""
    identified_bank = None
    for bank in banks:
        print(f"\n  Testing {bank.name}:")
        
        # Check sender emails
        if bank.sender_emails:
            for email in bank.sender_emails:
                if email.lower() in test_job.email_from.lower():
                    print(f"    ✅ MATCH - sender email: {email}")
                    identified_bank = bank
                    break
                else:
                    print(f"    ❌ No match - sender email: {email}")
        
        # Check sender domains
        if bank.sender_domains:
            for domain in bank.sender_domains:
                if domain.lower() in test_job.email_from.lower():
                    print(f"    ✅ MATCH - sender domain: {domain}")
                    identified_bank = bank
                    break
                else:
                    print(f"    ❌ No match - sender domain: {domain}")
        
        # Check subject for bank name
        if bank.name.lower() in test_job.email_subject.lower():
            print(f"    ✅ MATCH - bank name in subject: {bank.name}")
            identified_bank = bank
    
    if identified_bank:
        print(f"\n🎯 IDENTIFIED: {identified_bank.name}")
    else:
        print(f"\n❌ NO BANK IDENTIFIED FOR THIS EMAIL")

if __name__ == "__main__":
    main() 