#!/usr/bin/env python3
"""
Assign bank_id to existing EmailParsingJob records that don't have one
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import DatabaseSession
from app.models.email_parsing_job import EmailParsingJob
from app.models.bank import Bank

def identify_bank_for_email(email_from: str, email_subject: str, banks):
    """Identify bank using the same logic as TransactionCreationWorker"""
    for bank in banks:
        # Check sender emails
        if bank.sender_emails:
            for email in bank.sender_emails:
                if email.lower() in email_from.lower():
                    return bank
        
        # Check sender domains
        if bank.sender_domains:
            for domain in bank.sender_domains:
                if domain.lower() in email_from.lower():
                    return bank
        
        # Check subject for bank name
        if bank.name.lower() in email_subject.lower():
            return bank
    
    return None

def assign_bank_ids():
    print("🔧 ASSIGNING BANK IDs TO EXISTING EMAILS")
    print("=" * 60)
    
    with DatabaseSession() as db:
        # Get all active banks
        banks = db.query(Bank).filter_by(is_active=True).all()
        print(f"📋 Found {len(banks)} active banks")
        
        # Get all parsing jobs without bank_id
        jobs_without_bank = db.query(EmailParsingJob).filter(
            EmailParsingJob.bank_id.is_(None)
        ).all()
        
        print(f"📧 Found {len(jobs_without_bank)} emails without bank_id")
        
        if not jobs_without_bank:
            print("✅ All emails already have bank_id assigned")
            return
        
        updates_made = 0
        banks_identified = {}
        
        for job in jobs_without_bank:
            identified_bank = identify_bank_for_email(
                job.email_from, 
                job.email_subject, 
                banks
            )
            
            if identified_bank:
                job.bank_id = identified_bank.id
                updates_made += 1
                
                bank_name = identified_bank.name
                if bank_name not in banks_identified:
                    banks_identified[bank_name] = 0
                banks_identified[bank_name] += 1
                
                print(f"📧 Job {job.id}: {bank_name}")
            else:
                print(f"❌ Job {job.id}: No bank identified for {job.email_from}")
        
        # Commit changes
        if updates_made > 0:
            db.commit()
            print(f"\n💾 Committed {updates_made} updates to database")
            
            print(f"\n📊 SUMMARY:")
            print("-" * 40)
            for bank_name, count in banks_identified.items():
                print(f"  {bank_name}: {count} emails")
        else:
            print(f"\n⚠️  No updates made")
        
        # Verify results
        remaining_without_bank = db.query(EmailParsingJob).filter(
            EmailParsingJob.bank_id.is_(None)
        ).count()
        
        print(f"\n🔍 VERIFICATION:")
        print(f"  Emails still without bank_id: {remaining_without_bank}")
        
        if remaining_without_bank == 0:
            print("✅ All emails now have bank_id assigned!")
        else:
            print(f"⚠️  {remaining_without_bank} emails still need manual assignment")

if __name__ == "__main__":
    assign_bank_ids() 