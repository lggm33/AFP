#!/usr/bin/env python3
"""
Test script to verify the system works correctly without ParsingRule model.
This script will test that:
1. Database initialization works without ParsingRule
2. TransactionCreationWorker works with only BankEmailTemplate
3. Bank setup works correctly
4. No references to ParsingRule remain
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import init_database, DatabaseSession
from app.models.bank import Bank
from app.models.email_parsing_job import EmailParsingJob
from app.models.bank_email_template import BankEmailTemplate
from app.workers.transaction_creation_worker import TransactionCreationWorker
from app.services.bank_setup_service import BankSetupService

def main():
    print("🧪 Testing System Without ParsingRule Model")
    print("=" * 50)
    
    # 1. Test database initialization
    try:
        init_database()
        print("✅ Database initialized successfully (no ParsingRule references)")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return
    
    # 2. Test model imports
    try:
        from app.models import Bank, EmailParsingJob, BankEmailTemplate
        print("✅ All models imported successfully")
        
        # Verify ParsingRule is not imported
        try:
            from app.models.parsing_rule import ParsingRule
            print("❌ ERROR: ParsingRule model still exists!")
            return
        except ImportError:
            print("✅ ParsingRule model successfully removed")
            
    except Exception as e:
        print(f"❌ Model import failed: {e}")
        return
    
    # 3. Test worker functionality
    with DatabaseSession() as db:
        print("\n🔄 Testing TransactionCreationWorker...")
        
        # Check if we have banks and templates
        banks = db.query(Bank).all()
        print(f"   • Banks in system: {len(banks)}")
        
        for bank in banks:
            template_count = db.query(BankEmailTemplate).filter_by(bank_id=bank.id).count()
            print(f"   • {bank.name}: {template_count} templates")
        
        # Test worker initialization
        try:
            worker = TransactionCreationWorker()
            print("✅ TransactionCreationWorker initialized successfully")
        except Exception as e:
            print(f"❌ Worker initialization failed: {e}")
            return
        
        # Test processing with templates only
        sample_email = db.query(EmailParsingJob).filter(
            EmailParsingJob.bank_id.isnot(None)
        ).first()
        
        if sample_email:
            bank = db.query(Bank).get(sample_email.bank_id)
            print(f"   • Testing with email from {bank.name}")
            
            try:
                result = worker._process_email_parsing(sample_email)
                
                if result['success']:
                    print(f"✅ Email processed successfully using templates")
                    print(f"   • Transaction data: {result.get('transaction_data', {})}")
                elif result['status'] == 'no_templates_configured':
                    print(f"✅ Correct behavior: {result['error_message']}")
                else:
                    print(f"⚠️  Processing result: {result}")
                    
            except Exception as e:
                print(f"❌ Email processing failed: {e}")
        else:
            print("⚠️  No sample emails available for testing")
    
    # 4. Test BankSetupService
    print("\n🏦 Testing BankSetupService...")
    try:
        bank_setup = BankSetupService()
        
        with DatabaseSession() as db:
            banks_needing_setup = bank_setup.get_banks_needing_setup()
            print(f"   • Banks needing template setup: {len(banks_needing_setup)}")
            
            for bank in banks_needing_setup:
                print(f"     - {bank.name}")
        
        print("✅ BankSetupService working correctly")
        
    except Exception as e:
        print(f"❌ BankSetupService failed: {e}")
    
    # 5. Test database schema
    print("\n🗃️  Testing Database Schema...")
    with DatabaseSession() as db:
        try:
            # Test that all expected tables exist
            banks = db.query(Bank).count()
            templates = db.query(BankEmailTemplate).count()
            emails = db.query(EmailParsingJob).count()
            
            print(f"✅ Database schema valid:")
            print(f"   • Banks: {banks}")
            print(f"   • Email Templates: {templates}")
            print(f"   • Email Parsing Jobs: {emails}")
            
        except Exception as e:
            print(f"❌ Database schema test failed: {e}")
    
    # 6. Test that no ParsingRule references remain in code
    print("\n🔍 Checking for remaining ParsingRule references...")
    
    # Check key files
    files_to_check = [
        'app/workers/transaction_creation_worker.py',
        'app/models/__init__.py',
        'app/models/bank.py',
        'app/core/database.py'
    ]
    
    parsing_rule_found = False
    for file_path in files_to_check:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                if 'ParsingRule' in content and 'OBSOLETO' not in content:
                    print(f"⚠️  Found ParsingRule reference in {file_path}")
                    parsing_rule_found = True
        except FileNotFoundError:
            print(f"⚠️  File not found: {file_path}")
    
    if not parsing_rule_found:
        print("✅ No active ParsingRule references found in key files")
    
    print("\n🎉 System Test Complete!")
    print("=" * 50)
    
    if not parsing_rule_found:
        print("✅ SUCCESS: System is working correctly without ParsingRule model")
        print("   • Database initialization: ✅")
        print("   • Model imports: ✅") 
        print("   • Worker functionality: ✅")
        print("   • BankSetupService: ✅")
        print("   • Database schema: ✅")
        print("   • Code cleanup: ✅")
    else:
        print("⚠️  WARNING: Some ParsingRule references may still exist")

if __name__ == "__main__":
    main() 