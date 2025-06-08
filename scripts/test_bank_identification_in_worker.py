#!/usr/bin/env python3
"""
Test why bank identification is failing in the TransactionCreationWorker
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import DatabaseSession
from app.models.email_parsing_job import EmailParsingJob
from app.models.bank import Bank
from app.workers.transaction_creation_worker import TransactionCreationWorker

def test_worker_bank_identification():
    print("🔍 TESTING WORKER BANK IDENTIFICATION")
    print("=" * 60)
    
    worker = TransactionCreationWorker()
    
    with DatabaseSession() as db:
        # Get a recent email without bank_id
        email_job = db.query(EmailParsingJob).filter(
            EmailParsingJob.bank_id.is_(None)
        ).first()
        
        if not email_job:
            print("❌ No emails without bank_id found")
            return
        
        print(f"📧 Testing email job {email_job.id}:")
        print(f"  From: {email_job.email_from}")
        print(f"  Subject: {email_job.email_subject}")
        print(f"  Current bank_id: {email_job.bank_id}")
        
        # Test the worker's _identify_bank method directly
        print(f"\n🔍 Testing worker._identify_bank()...")
        identified_bank = worker._identify_bank(
            email_job.email_from, 
            email_job.email_subject
        )
        
        if identified_bank:
            print(f"✅ Worker identified: {identified_bank.name} (ID: {identified_bank.id})")
        else:
            print(f"❌ Worker failed to identify bank")
        
        # Let's also test the identification logic manually
        print(f"\n🔍 Testing manual identification logic...")
        banks = db.query(Bank).filter_by(is_active=True).all()
        
        print(f"Available banks:")
        for bank in banks:
            print(f"  {bank.name}: emails={bank.sender_emails}, domains={bank.sender_domains}")
        
        print(f"\nTesting against email: {email_job.email_from}")
        
        for bank in banks:
            print(f"\n  Testing {bank.name}:")
            
            # Check sender emails
            if bank.sender_emails:
                for email in bank.sender_emails:
                    is_match = email.lower() in email_job.email_from.lower()
                    print(f"    Email '{email}' in '{email_job.email_from}': {is_match}")
                    if is_match:
                        print(f"    ✅ MATCH FOUND!")
            
            # Check sender domains
            if bank.sender_domains:
                for domain in bank.sender_domains:
                    is_match = domain.lower() in email_job.email_from.lower()
                    print(f"    Domain '{domain}' in '{email_job.email_from}': {is_match}")
                    if is_match:
                        print(f"    ✅ MATCH FOUND!")

def test_worker_processing():
    print("\n🔄 TESTING FULL WORKER PROCESSING")
    print("=" * 60)
    
    worker = TransactionCreationWorker()
    
    with DatabaseSession() as db:
        # Get a recent email without bank_id
        email_job = db.query(EmailParsingJob).filter(
            EmailParsingJob.bank_id.is_(None)
        ).first()
        
        if not email_job:
            print("❌ No emails without bank_id found")
            return
        
        print(f"📧 Processing email job {email_job.id} with worker...")
        
        try:
            # Test the full processing method
            result = worker._process_email_parsing(email_job)
            
            print(f"📊 Worker processing result:")
            print(f"  Success: {result['success']}")
            print(f"  Status: {result.get('status', 'N/A')}")
            print(f"  Error: {result.get('error_message', 'N/A')}")
            
            # Check if bank_id was assigned
            db.refresh(email_job)
            print(f"  Bank ID after processing: {email_job.bank_id}")
            
        except Exception as e:
            print(f"❌ Worker processing failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_worker_bank_identification()
    test_worker_processing() 