#!/usr/bin/env python3
"""
Test script for the new bank setup flow with templates.
This tests the new approach where templates are generated during setup,
not during transaction processing.
"""
import sys
import os
from datetime import datetime, UTC
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import init_database, DatabaseSession
from app.models.bank import Bank
from app.models.email_parsing_job import EmailParsingJob
from app.models.bank_email_template import BankEmailTemplate
from app.services.bank_setup_service import BankSetupService
from app.workers.transaction_creation_worker import TransactionCreationWorker
from app.models.email_import_job import EmailImportJob
from app.models.integration import Integration

def test_bank_setup_service():
    """Test the new BankSetupService"""
    print("🏦 Testing Bank Setup Service")
    print("=" * 50)
    
    setup_service = BankSetupService()
    
    with DatabaseSession() as db:
        # Clear existing data for clean test
        print("🧹 Clearing existing templates...")
        db.query(BankEmailTemplate).delete()
        db.commit()
        
        # Test setup of default banks
        print("🚀 Setting up default Costa Rican banks...")
        results = setup_service.setup_default_costa_rican_banks()
        
        print(f"\n📊 Setup Results:")
        for result in results:
            if result['success']:
                print(f"   ✅ {result['bank_name']}: {result['templates_created']} templates created")
            else:
                print(f"   ❌ {result['bank_name']}: {result.get('error', 'Unknown error')}")
        
        # Verify templates were created
        total_templates = db.query(BankEmailTemplate).count()
        print(f"\n🎯 Total templates in database: {total_templates}")
        
        # Show template details
        if total_templates > 0:
            templates = db.query(BankEmailTemplate).all()
            print(f"\n📋 Template Details:")
            for template in templates:
                bank = db.query(Bank).get(template.bank_id)
                print(f"   • {bank.name}: '{template.template_name}' (Type: {template.template_type})")

def test_worker_with_templates():
    """Test worker behavior when templates exist"""
    print("\n⚙️ Testing Worker with Configured Templates")
    print("=" * 50)
    
    worker = TransactionCreationWorker()
    
    with DatabaseSession() as db:
        # Find an email to test with
        parsing_job = db.query(EmailParsingJob).filter(
            EmailParsingJob.bank_id.isnot(None)
        ).first()
        
        if not parsing_job:
            print("❌ No parsing job found for testing")
            return
        
        bank = db.query(Bank).get(parsing_job.bank_id)
        print(f"📧 Testing with email from {bank.name}")
        
        # Check if templates exist for this bank
        templates = db.query(BankEmailTemplate).filter_by(
            bank_id=bank.id,
            is_active=True
        ).all()
        
        print(f"📋 Found {len(templates)} templates for {bank.name}")
        
        if templates:
            for template in templates:
                print(f"   • {template.template_name} (Priority: {template.priority})")
        
        # Test worker processing
        try:
            print(f"\n🔄 Processing email with worker...")
            result = worker._process_email_parsing(parsing_job)
            
            print(f"✅ Worker processing completed:")
            print(f"   Success: {result['success']}")
            print(f"   Status: {result.get('status', 'N/A')}")
            
            if result['success']:
                print(f"   Transaction created: {result['transaction_id']}")
                print(f"   Confidence: {result['confidence_score']:.2f}")
                print(f"   Rules used: {result['rules_used']}")
            else:
                print(f"   Error: {result.get('error_message', 'N/A')}")
                
        except Exception as e:
            print(f"❌ Worker error: {str(e)}")
            import traceback
            traceback.print_exc()

def test_worker_without_templates():
    """Test worker behavior when no templates exist"""
    print("\n🚫 Testing Worker without Templates")
    print("=" * 50)
    
    worker = TransactionCreationWorker()
    
    with DatabaseSession() as db:
        # Create a test bank without templates
        test_bank = Bank(
            name="Test Bank Without Templates",
            bank_code="TEST",
            domain="testbank.com",
            sender_emails=["test@testbank.com"],
            sender_domains=["testbank.com"],
            country_code="CR",
            bank_type="commercial",
            parsing_priority=10,
            confidence_threshold=0.7,
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.add(test_bank)
        db.commit()
        
        # Create a test parsing job
        # First we need an EmailImportJob to link to
        integration = db.query(Integration).first()
        if not integration:
            print("❌ No integration found for test")
            return
        
        # Create a test EmailImportJob
        test_import_job = EmailImportJob(
            integration_id=integration.id,
            status='completed',
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.add(test_import_job)
        db.commit()
        
        test_job = EmailParsingJob(
            email_import_job_id=test_import_job.id,  # Required field
            bank_id=test_bank.id,
            email_message_id="test_message_123",  # Required field
            email_subject="Test Transaction",
            email_from="test@testbank.com",
            email_body="Test email body",
            status="waiting",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.add(test_job)
        db.commit()
        
        print(f"🏦 Created test bank: {test_bank.name} (ID: {test_bank.id})")
        print(f"📧 Created test email job: {test_job.id}")
        
        # Verify no templates exist
        templates_count = db.query(BankEmailTemplate).filter_by(
            bank_id=test_bank.id
        ).count()
        print(f"📋 Templates for test bank: {templates_count}")
        
        # Test worker processing
        try:
            print(f"\n🔄 Processing email without templates...")
            result = worker._process_email_parsing(test_job)
            
            print(f"📊 Worker result:")
            print(f"   Success: {result['success']}")
            print(f"   Status: {result.get('status', 'N/A')}")
            print(f"   Error: {result.get('error_message', 'N/A')}")
            
            # Should fail with specific error
            if not result['success'] and result.get('status') == 'no_templates_configured':
                print("✅ Correct behavior: Worker returns error when no templates configured")
            else:
                print("❌ Unexpected behavior: Worker should return 'no_templates_configured' error")
                
        except Exception as e:
            print(f"❌ Worker error: {str(e)}")
            
        finally:
            # Clean up test data
            db.delete(test_job)
            db.delete(test_import_job)
            db.delete(test_bank)
            db.commit()
            print("🧹 Cleaned up test data")

def test_validation_functions():
    """Test bank validation functions"""
    print("\n✅ Testing Bank Validation")
    print("=" * 50)
    
    setup_service = BankSetupService()
    
    with DatabaseSession() as db:
        # Get all banks
        banks = db.query(Bank).all()
        
        print(f"🏦 Validating {len(banks)} banks...")
        
        for bank in banks:
            validation = setup_service.validate_bank_configuration(bank.id)
            
            if validation['valid']:
                print(f"   ✅ {validation['bank_name']}: {validation['templates_count']} templates")
            else:
                print(f"   ❌ {validation['bank_name']}: {validation['error']}")
        
        # Check banks needing setup
        needs_setup = setup_service.get_banks_needing_setup()
        
        if needs_setup:
            print(f"\n⚠️  Banks needing template setup:")
            for bank_info in needs_setup:
                print(f"   • {bank_info['bank_name']} (ID: {bank_info['bank_id']})")
        else:
            print(f"\n✅ All banks have templates configured")

def main():
    print("🧪 Testing New Bank Setup Flow")
    print("=" * 60)
    
    # Initialize database
    try:
        init_database()
        print("✅ Database initialized")
    except Exception as e:
        print(f"❌ Database error: {e}")
        return
    
    # Run tests
    test_bank_setup_service()
    test_worker_with_templates()
    test_worker_without_templates()
    test_validation_functions()
    
    print("\n✅ All Bank Setup Tests Complete!")
    print("=" * 60)

if __name__ == "__main__":
    main() 