#!/usr/bin/env python3
"""
Script to create all banks found in the EmailParsingJob data.
This will enable AI to generate rules for different bank email formats.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import init_database, db
from app.models.email_parsing_job import EmailParsingJob
from app.models.bank import Bank
from datetime import datetime, UTC

def create_all_banks():
    """Create banks for all email senders found in the database"""
    print("🏦 CREATING ALL BANKS FROM EMAIL DATA")
    print("="*60)
    
    try:
        # Get unique email senders
        email_jobs = db.session.query(EmailParsingJob.email_from).distinct().all()
        
        banks_to_create = []
        
        for (email_from,) in email_jobs:
            print(f"📧 Found email from: {email_from}")
            
            # Determine bank based on email
            if "scotiabank" in email_from.lower():
                banks_to_create.append({
                    'name': 'Scotiabank Costa Rica',
                    'domain': '@scotiabank.com',
                    'sender_emails': ['AlertasScotiabank@scotiabank.com'],
                    'sender_domains': ['@scotiabank.com'],
                    'keywords': ['alerta', 'transacción', 'tarjeta', 'crédito'],
                    'bank_code': 'SCOTI'
                })
            elif "bancobcr" in email_from.lower() or "mensajero" in email_from.lower():
                banks_to_create.append({
                    'name': 'Banco de Costa Rica',
                    'domain': '@bancobcr.com', 
                    'sender_emails': ['mensajero@bancobcr.com'],
                    'sender_domains': ['@bancobcr.com'],
                    'keywords': ['sinpemovil', 'notificación', 'transacción'],
                    'bank_code': 'BCR'
                })
            elif "notificacionesbaccr" in email_from.lower():
                # BAC already exists, skip
                continue
        
        # Remove duplicates
        unique_banks = []
        seen_names = set()
        for bank in banks_to_create:
            if bank['name'] not in seen_names:
                unique_banks.append(bank)
                seen_names.add(bank['name'])
        
        # Create banks
        created_count = 0
        for bank_data in unique_banks:
            existing_bank = db.session.query(Bank).filter_by(name=bank_data['name']).first()
            
            if existing_bank:
                print(f"✅ {bank_data['name']} already exists (ID: {existing_bank.id})")
                continue
            
            new_bank = Bank(
                name=bank_data['name'],
                domain=bank_data['domain'],
                country_code="CR",  # Costa Rica
                bank_code=bank_data['bank_code'],
                bank_type="commercial",
                is_active=True,
                sender_domains=bank_data['sender_domains'],
                sender_emails=bank_data['sender_emails'],
                keywords=bank_data['keywords'],
                parsing_priority=10,
                website=f"https://www.{bank_data['bank_code'].lower()}.co.cr",
                confidence_threshold=0.8,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            
            db.session.add(new_bank)
            created_count += 1
            print(f"✅ Created {bank_data['name']} (Code: {bank_data['bank_code']})")
        
        db.session.commit()
        print(f"\n🎯 Created {created_count} new banks")
        
    except Exception as e:
        print(f"❌ Error creating banks: {str(e)}")
        db.session.rollback()

def update_email_jobs_with_banks():
    """Update EmailParsingJobs to reference their corresponding banks"""
    print("\n📧 UPDATING EMAIL JOBS WITH BANK REFERENCES")
    print("="*60)
    
    try:
        # Get all banks
        banks = db.session.query(Bank).all()
        
        updated_count = 0
        for bank in banks:
            print(f"\n🏦 Processing bank: {bank.name}")
            
            # Find emails that match this bank
            for sender_email in bank.sender_emails or []:
                matching_jobs = db.session.query(EmailParsingJob).filter(
                    EmailParsingJob.email_from.like(f'%{sender_email}%'),
                    EmailParsingJob.bank_id.is_(None)
                ).all()
                
                for job in matching_jobs:
                    job.bank_id = bank.id
                    updated_count += 1
                    print(f"  ✅ Linked EmailParsingJob {job.id} to {bank.name}")
        
        db.session.commit()
        print(f"\n🎯 Updated {updated_count} EmailParsingJobs with bank references")
        
    except Exception as e:
        print(f"❌ Error updating email jobs: {str(e)}")
        db.session.rollback()

def show_bank_summary():
    """Show summary of all banks and their email assignments"""
    print("\n📊 BANK SUMMARY")
    print("="*60)
    
    try:
        banks = db.session.query(Bank).all()
        
        for bank in banks:
            email_count = db.session.query(EmailParsingJob).filter_by(bank_id=bank.id).count()
            print(f"\n🏦 {bank.name} (ID: {bank.id})")
            print(f"   Code: {bank.bank_code}")
            print(f"   Sender Emails: {bank.sender_emails}")
            print(f"   Sender Domains: {bank.sender_domains}")
            print(f"   Keywords: {bank.keywords}")
            print(f"   EmailParsingJobs: {email_count}")
        
        # Show unassigned emails
        unassigned_count = db.session.query(EmailParsingJob).filter(
            EmailParsingJob.bank_id.is_(None)
        ).count()
        
        if unassigned_count > 0:
            print(f"\n⚠️  Unassigned EmailParsingJobs: {unassigned_count}")
            
            # Show sample unassigned emails
            unassigned_emails = db.session.query(EmailParsingJob).filter(
                EmailParsingJob.bank_id.is_(None)
            ).limit(5).all()
            
            print("   Sample unassigned emails:")
            for job in unassigned_emails:
                print(f"   - ID {job.id}: {job.email_from}")
        
    except Exception as e:
        print(f"❌ Error showing bank summary: {str(e)}")

def main():
    """Main function"""
    try:
        # Initialize database
        init_database()
        print("✅ Database connection established")
        
        # Create all banks
        create_all_banks()
        
        # Update email jobs
        update_email_jobs_with_banks()
        
        # Show summary
        show_bank_summary()
        
        print("\n" + "="*60)
        print("✅ ALL BANKS SETUP COMPLETE")
        print("="*60)
        print("🎯 Ready for AI to generate parsing rules for:")
        print("1. BAC Costa Rica (notificaciones transacciones)")
        print("2. Scotiabank Costa Rica (alertas tarjeta)")
        print("3. Banco de Costa Rica (SINPEMOVIL)")
        print("\nAI will automatically generate regex patterns for each bank!")
        
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 