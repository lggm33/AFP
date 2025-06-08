#!/usr/bin/env python3
"""
Debug script to identify which emails are still causing no_bank_identified errors
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import DatabaseSession
from app.models.email_parsing_job import EmailParsingJob
from app.models.bank import Bank

def main():
    print("🔍 DEBUGGING PROBLEMATIC EMAILS")
    print("=" * 60)
    
    with DatabaseSession() as db:
        # Get recent parsing jobs that might be problematic
        jobs = db.query(EmailParsingJob).order_by(EmailParsingJob.id.desc()).limit(15).all()
        
        print("📧 RECENT EMAIL PARSING JOBS:")
        print("-" * 60)
        for job in jobs:
            bank_name = "None"
            if job.bank_id:
                bank = db.query(Bank).get(job.bank_id)
                bank_name = bank.name if bank else f"Bank ID {job.bank_id} (NOT FOUND)"
            
            print(f"Job {job.id:2d}: Bank={bank_name}")
            print(f"         From: {job.email_from}")
            print(f"         Subject: {job.email_subject[:50]}...")
            print()
        
        # Get all active banks for reference
        banks = db.query(Bank).filter_by(is_active=True).all()
        print("\n🏦 CURRENT BANK CONFIGURATIONS:")
        print("-" * 60)
        for bank in banks:
            print(f"{bank.name} (ID: {bank.id})")
            print(f"  emails: {bank.sender_emails}")
            print(f"  domains: {bank.sender_domains}")
            print()
        
        # Check specific problematic jobs mentioned in logs
        problematic_job_ids = [8, 9, 17, 18, 11, 12]
        print(f"\n🚨 CHECKING SPECIFIC PROBLEMATIC JOBS:")
        print("-" * 60)
        
        for job_id in problematic_job_ids:
            job = db.query(EmailParsingJob).get(job_id)
            if not job:
                print(f"Job {job_id}: NOT FOUND")
                continue
            
            print(f"\nJob {job_id}:")
            print(f"  Bank ID: {job.bank_id}")
            print(f"  From: {job.email_from}")
            print(f"  Subject: {job.email_subject}")
            
            # Try to identify bank manually
            identified_bank = None
            for bank in banks:
                # Check sender emails
                if bank.sender_emails:
                    for email in bank.sender_emails:
                        if email.lower() in job.email_from.lower():
                            identified_bank = bank
                            break
                
                # Check sender domains
                if bank.sender_domains:
                    for domain in bank.sender_domains:
                        if domain.lower() in job.email_from.lower():
                            identified_bank = bank
                            break
                
                if identified_bank:
                    break
            
            if identified_bank:
                print(f"  ✅ Should identify as: {identified_bank.name}")
                if job.bank_id != identified_bank.id:
                    print(f"  ⚠️  MISMATCH: Has bank_id={job.bank_id}, should be {identified_bank.id}")
            else:
                print(f"  ❌ Cannot identify bank for this email")
        
        # Check if there are any emails without bank_id
        emails_without_bank = db.query(EmailParsingJob).filter(
            EmailParsingJob.bank_id.is_(None)
        ).count()
        
        print(f"\n📊 SUMMARY:")
        print(f"  Total emails without bank_id: {emails_without_bank}")
        
        if emails_without_bank > 0:
            print(f"  ⚠️  Some emails still need bank_id assignment")
        else:
            print(f"  ✅ All emails have bank_id assigned")

if __name__ == "__main__":
    main() 