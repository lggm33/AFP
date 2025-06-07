#!/usr/bin/env python3
"""
Script to inspect email content and create corresponding bank.
Based on the verification, we have emails from BAC Costa Rica.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import init_database, db
from app.models.email_parsing_job import EmailParsingJob
from app.models.bank import Bank
from datetime import datetime, UTC

def inspect_email_content():
    """Inspect the full content of an email to understand structure"""
    print("🔍 EMAIL CONTENT INSPECTION")
    print("="*60)
    
    try:
        # Get first email
        email_job = db.session.query(EmailParsingJob).first()
        
        if not email_job:
            print("❌ No emails found in database")
            return
        
        print(f"📧 Inspecting Email ID: {email_job.id}")
        print(f"From: {email_job.email_from}")
        print(f"Subject: {email_job.email_subject}")
        print(f"Message ID: {email_job.email_message_id}")
        print(f"Status: {email_job.parsing_status}")
        print(f"Body Length: {len(email_job.email_body)} characters")
        
        print("\n" + "="*60)
        print("EMAIL BODY CONTENT:")
        print("="*60)
        print(email_job.email_body)
        
    except Exception as e:
        print(f"❌ Error inspecting email: {str(e)}")

def create_bac_bank():
    """Create BAC Costa Rica bank based on the emails we found"""
    print("\n🏦 CREATING BAC COSTA RICA BANK")
    print("="*60)
    
    try:
        # Check if BAC bank already exists
        existing_bank = db.session.query(Bank).filter_by(name="BAC Costa Rica").first()
        
        if existing_bank:
            print(f"✅ BAC Costa Rica bank already exists (ID: {existing_bank.id})")
            return existing_bank
        
        # Create new BAC bank
        bac_bank = Bank(
            name="BAC Costa Rica",
            domain="@notificacionesbaccr.com",  # Primary domain
            country_code="CR",  # Costa Rica
            bank_code="BAC",
            bank_type="commercial",
            is_active=True,
            sender_domains=["@notificacionesbaccr.com", "@baccredomatic.com"],
            sender_emails=["notificacion@notificacionesbaccr.com"],
            keywords=["transacción", "compra", "retiro", "transferencia", "notificación"],
            parsing_priority=10,  # High priority
            website="https://www.baccredomatic.com/",
            confidence_threshold=0.8,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        
        db.session.add(bac_bank)
        db.session.commit()
        
        print(f"✅ Created BAC Costa Rica bank (ID: {bac_bank.id})")
        print(f"   Email patterns: {bac_bank.email_patterns}")
        
        return bac_bank
        
    except Exception as e:
        print(f"❌ Error creating BAC bank: {str(e)}")
        db.session.rollback()
        return None

def update_email_jobs_with_bank():
    """Update existing EmailParsingJobs to reference the BAC bank"""
    print("\n📧 UPDATING EMAIL JOBS WITH BANK REFERENCE")
    print("="*60)
    
    try:
        # Get BAC bank
        bac_bank = db.session.query(Bank).filter_by(name="BAC Costa Rica").first()
        
        if not bac_bank:
            print("❌ BAC bank not found")
            return
        
        # Update all BAC emails to reference the bank
        bac_emails = db.session.query(EmailParsingJob).filter(
            EmailParsingJob.email_from.like('%notificacionesbaccr.com%')
        ).all()
        
        updated_count = 0
        for email_job in bac_emails:
            if email_job.bank_id is None:
                email_job.bank_id = bac_bank.id
                updated_count += 1
        
        db.session.commit()
        
        print(f"✅ Updated {updated_count} EmailParsingJobs with BAC bank reference")
        
    except Exception as e:
        print(f"❌ Error updating email jobs: {str(e)}")
        db.session.rollback()

def show_sample_transaction_data():
    """Extract sample transaction data from email subjects to understand pattern"""
    print("\n💳 SAMPLE TRANSACTION DATA FROM SUBJECTS")
    print("="*60)
    
    try:
        email_jobs = db.session.query(EmailParsingJob).limit(10).all()
        
        print("Sample subjects to understand transaction patterns:")
        for job in email_jobs:
            print(f"- {job.email_subject}")
            
        print(f"\n📊 Pattern Analysis:")
        print("Format appears to be: 'Notificación de transacción [MERCHANT] [DATE] - [TIME]'")
        print("Examples:")
        print("- GORDI FRUTI 06-06-2025 - 11:45")
        print("- AUTO MERCADO SAN FR 16-05-2025 - 15:49") 
        print("- COBRO ADMINISTRACION C 16-05-2025 - 15:40")
        
        print(f"\n🤖 AI will need to extract from HTML body:")
        print("- Amount (from HTML content)")
        print("- Merchant (from subject)")
        print("- Date/Time (from subject)")
        print("- Transaction type (debit/credit)")
        
    except Exception as e:
        print(f"❌ Error analyzing transaction data: {str(e)}")

def main():
    """Main function"""
    try:
        # Initialize database
        init_database()
        print("✅ Database connection established")
        
        # Run inspections
        inspect_email_content()
        
        # Create BAC bank
        create_bac_bank()
        
        # Update email jobs
        update_email_jobs_with_bank()
        
        # Show transaction patterns
        show_sample_transaction_data()
        
        print("\n" + "="*60)
        print("✅ INSPECTION AND SETUP COMPLETE")
        print("="*60)
        print("🎯 Ready for AI integration:")
        print("1. BAC Costa Rica bank created")
        print("2. Email jobs linked to bank")
        print("3. Transaction patterns identified")
        print("4. AI can now generate parsing rules")
        
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 