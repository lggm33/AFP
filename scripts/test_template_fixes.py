#!/usr/bin/env python3
"""
Test script to verify the template system fixes:
1. SQLAlchemy session issues are resolved
2. No duplicate template generation occurs
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import init_database, DatabaseSession
from app.models.bank import Bank
from app.models.email_parsing_job import EmailParsingJob
from app.models.bank_email_template import BankEmailTemplate
from app.services.bank_template_service import BankTemplateService
from app.workers.transaction_creation_worker import TransactionCreationWorker
import threading
import time

def test_no_duplicate_templates():
    """Test that multiple workers don't create duplicate templates"""
    print("🔒 Testing Duplicate Template Prevention")
    print("=" * 50)
    
    template_service = BankTemplateService()
    
    with DatabaseSession() as db:
        # Clear existing templates for BAC Costa Rica
        bank = db.query(Bank).filter_by(name="BAC Costa Rica").first()
        if not bank:
            print("❌ BAC Costa Rica not found")
            return
        
        # Delete existing templates
        existing_templates = db.query(BankEmailTemplate).filter_by(bank_id=bank.id).all()
        for template in existing_templates:
            db.delete(template)
        db.commit()
        
        print(f"✅ Cleared {len(existing_templates)} existing templates for {bank.name}")
        
        # Get sample emails
        sample_emails = db.query(EmailParsingJob).filter_by(
            bank_id=bank.id
        ).limit(3).all()
        
        if not sample_emails:
            print("❌ No sample emails found")
            return
        
        print(f"📧 Found {len(sample_emails)} sample emails")
        
        # Simulate multiple workers trying to generate templates simultaneously
        results = []
        
        def worker_generate_template(worker_id):
            """Simulate a worker generating a template"""
            try:
                service = BankTemplateService()
                template = service.auto_generate_template(bank.id, sample_emails)
                results.append(f"Worker {worker_id}: {'SUCCESS' if template else 'FAILED'}")
                if template:
                    results.append(f"  Template ID: {template.id}, Name: {template.template_name}")
            except Exception as e:
                results.append(f"Worker {worker_id}: ERROR - {str(e)}")
        
        # Create 3 threads to simulate concurrent workers
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker_generate_template, args=(i+1,))
            threads.append(thread)
        
        # Start all threads simultaneously
        print("🚀 Starting 3 concurrent workers...")
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Print results
        print("\n📊 Worker Results:")
        for result in results:
            print(f"   {result}")
        
        # Check final template count
        final_templates = db.query(BankEmailTemplate).filter_by(bank_id=bank.id).count()
        print(f"\n🎯 Final template count for {bank.name}: {final_templates}")
        
        if final_templates == 1:
            print("✅ SUCCESS: Only one template created despite multiple workers")
        else:
            print(f"❌ FAILED: {final_templates} templates created (should be 1)")

def test_session_fixes():
    """Test that SQLAlchemy session issues are resolved"""
    print("\n💾 Testing SQLAlchemy Session Fixes")
    print("=" * 50)
    
    worker = TransactionCreationWorker()
    template_service = BankTemplateService()
    
    with DatabaseSession() as db:
        # Get a test email
        parsing_job = db.query(EmailParsingJob).filter(
            EmailParsingJob.bank_id.isnot(None)
        ).first()
        
        if not parsing_job:
            print("❌ No parsing job found for testing")
            return
        
        bank = db.query(Bank).get(parsing_job.bank_id)
        print(f"📧 Testing with email from {bank.name}")
        
        try:
            # Test find_best_template (now returns ID)
            template_id = template_service.find_best_template(
                bank.id,
                parsing_job.email_subject or '',
                parsing_job.email_from or '',
                parsing_job.email_body or ''
            )
            
            if template_id:
                print(f"✅ find_best_template returned ID: {template_id}")
                
                # Test loading template in worker session
                template = db.query(BankEmailTemplate).get(template_id)
                if template:
                    print(f"✅ Successfully loaded template: {template.template_name}")
                    
                    # Test extract_transaction_data
                    extraction_result = template_service.extract_transaction_data(
                        template,
                        parsing_job.email_body or ''
                    )
                    
                    print(f"✅ extract_transaction_data completed")
                    print(f"   Confidence: {extraction_result['confidence_score']:.2f}")
                    print(f"   Data: {extraction_result['extracted_data']}")
                    
                else:
                    print(f"❌ Failed to load template {template_id}")
            else:
                print("⚠️  No matching template found")
                
                # Test template generation
                sample_emails = db.query(EmailParsingJob).filter_by(
                    bank_id=bank.id
                ).limit(2).all()
                
                if sample_emails:
                    print("🤖 Testing template generation...")
                    new_template = template_service.auto_generate_template(
                        bank.id,
                        sample_emails
                    )
                    
                    if new_template:
                        print(f"✅ Template generation successful: {new_template.template_name}")
                        
                        # Test using the newly generated template
                        extraction_result = template_service.extract_transaction_data(
                            new_template,
                            parsing_job.email_body or ''
                        )
                        
                        print(f"✅ New template extraction completed")
                        print(f"   Confidence: {extraction_result['confidence_score']:.2f}")
                    else:
                        print("❌ Template generation failed")
                        
        except Exception as e:
            print(f"❌ Session error occurred: {str(e)}")
            import traceback
            traceback.print_exc()
            return
        
        print("✅ No SQLAlchemy session errors detected")

def test_worker_processing():
    """Test the full worker processing with fixes"""
    print("\n⚙️ Testing Worker Processing")
    print("=" * 50)
    
    worker = TransactionCreationWorker()
    
    with DatabaseSession() as db:
        # Get a test email
        parsing_job = db.query(EmailParsingJob).filter(
            EmailParsingJob.bank_id.isnot(None),
            EmailParsingJob.status == 'waiting'
        ).first()
        
        if not parsing_job:
            print("❌ No waiting parsing job found")
            return
        
        print(f"📧 Testing worker processing with EmailParsingJob {parsing_job.id}")
        
        try:
            # Test the worker's _process_email_parsing method
            result = worker._process_email_parsing(parsing_job)
            
            print(f"✅ Worker processing completed")
            print(f"   Success: {result['success']}")
            print(f"   Status: {result.get('status', 'N/A')}")
            
            if result['success']:
                print(f"   Transaction ID: {result['transaction_id']}")
                print(f"   Confidence: {result['confidence_score']:.2f}")
                print(f"   Rules used: {result['rules_used']}")
            else:
                print(f"   Error: {result.get('error_message', 'N/A')}")
                
        except Exception as e:
            print(f"❌ Worker processing error: {str(e)}")
            import traceback
            traceback.print_exc()

def main():
    print("🧪 Testing Template System Fixes")
    print("=" * 60)
    
    # Initialize database
    try:
        init_database()
        print("✅ Database initialized")
    except Exception as e:
        print(f"❌ Database error: {e}")
        return
    
    # Run tests
    test_no_duplicate_templates()
    test_session_fixes()
    test_worker_processing()
    
    print("\n✅ All Template System Tests Complete!")
    print("=" * 60)

if __name__ == "__main__":
    main() 