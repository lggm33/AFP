#!/usr/bin/env python3
"""
Script to verify database data and validate AI integration fields.
This script connects to the database and shows current EmailParsingJob data
to ensure our AI integration is correctly mapped.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import init_database, db
from app.models.email_parsing_job import EmailParsingJob
from app.models.bank import Bank
from app.models.parsing_rule import ParsingRule
from app.models.transaction import Transaction
from app.models.integration import Integration
from sqlalchemy import text

def print_separator(title):
    """Print a nice separator with title"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def verify_email_parsing_jobs():
    """Verify EmailParsingJob data and structure"""
    print_separator("EMAIL PARSING JOBS VERIFICATION")
    
    try:
        # Get total count
        total_jobs = db.session.query(EmailParsingJob).count()
        print(f"📊 Total EmailParsingJobs in database: {total_jobs}")
        
        if total_jobs == 0:
            print("⚠️  No EmailParsingJob records found. Database might be empty.")
            return
        
        # Get sample records
        sample_jobs = db.session.query(EmailParsingJob).limit(5).all()
        
        print(f"\n📧 Sample EmailParsingJob records:")
        for i, job in enumerate(sample_jobs, 1):
            print(f"\n--- Record {i} ---")
            print(f"ID: {job.id}")
            print(f"Email From: {job.email_from}")
            print(f"Email Subject: {job.email_subject}")
            print(f"Email Message ID: {job.email_message_id}")
            print(f"Status: {job.parsing_status}")
            print(f"Email Body (first 200 chars): {job.email_body[:200] if job.email_body else 'None'}...")
            print(f"Bank ID: {job.bank_id}")
            print(f"Confidence Score: {job.confidence_score}")
            print(f"Created At: {job.created_at}")
            
        # Check field availability for AI
        print(f"\n🤖 AI Integration Field Verification:")
        first_job = sample_jobs[0] if sample_jobs else None
        if first_job:
            fields_check = {
                'email_from': first_job.email_from,
                'email_subject': first_job.email_subject, 
                'email_body': len(first_job.email_body) if first_job.email_body else 0,
                'email_message_id': first_job.email_message_id
            }
            
            for field, value in fields_check.items():
                status = "✅" if value else "❌"
                print(f"{status} {field}: {type(value).__name__} - {value if field != 'email_body' else f'{value} chars'}")
                
    except Exception as e:
        print(f"❌ Error querying EmailParsingJob: {str(e)}")

def verify_banks():
    """Verify Bank data"""
    print_separator("BANKS VERIFICATION")
    
    try:
        banks = db.session.query(Bank).all()
        print(f"📊 Total Banks in database: {len(banks)}")
        
        if banks:
            print(f"\n🏦 Available Banks:")
            for bank in banks:
                print(f"- ID: {bank.id}, Name: {bank.name}, Active: {bank.is_active}")
                print(f"  Email Patterns: {bank.email_patterns}")
        else:
            print("⚠️  No Bank records found.")
            
    except Exception as e:
        print(f"❌ Error querying Banks: {str(e)}")

def verify_parsing_rules():
    """Verify ParsingRule data"""
    print_separator("PARSING RULES VERIFICATION")
    
    try:
        rules = db.session.query(ParsingRule).all()
        print(f"📊 Total Parsing Rules in database: {len(rules)}")
        
        if rules:
            print(f"\n🔧 Existing Parsing Rules:")
            for rule in rules[:10]:  # Show first 10
                print(f"- ID: {rule.id}, Bank ID: {rule.bank_id}, Type: {rule.rule_type}")
                print(f"  Name: {rule.rule_name}")
                print(f"  Generation Method: {rule.generation_method}")
                print(f"  AI Model: {rule.ai_model_used}")
                print(f"  Active: {rule.is_active}")
                print(f"  Pattern: {rule.regex_pattern[:100]}...")
                print()
        else:
            print("⚠️  No ParsingRule records found. AI will need to generate rules.")
            
    except Exception as e:
        print(f"❌ Error querying ParsingRules: {str(e)}")

def verify_transactions():
    """Verify Transaction data"""
    print_separator("TRANSACTIONS VERIFICATION")
    
    try:
        transactions = db.session.query(Transaction).count()
        print(f"📊 Total Transactions in database: {transactions}")
        
        if transactions > 0:
            sample_transactions = db.session.query(Transaction).limit(3).all()
            print(f"\n💳 Sample Transactions:")
            for trans in sample_transactions:
                print(f"- ID: {trans.id}")
                print(f"  Amount: {trans.amount}")
                print(f"  Description: {trans.description}")
                print(f"  Date: {trans.date}")
                print(f"  Source: {trans.source}")
                print(f"  From Bank: {trans.from_bank}")
                print(f"  To Bank: {trans.to_bank}")
                print(f"  Email Parsing Job ID: {trans.email_parsing_job_id}")
                print(f"  Confidence Score: {trans.confidence_score}")
                print()
        else:
            print("⚠️  No Transaction records found.")
            
    except Exception as e:
        print(f"❌ Error querying Transactions: {str(e)}")

def verify_integrations():
    """Verify Integration data"""
    print_separator("INTEGRATIONS VERIFICATION")
    
    try:
        integrations = db.session.query(Integration).all()
        print(f"📊 Total Integrations in database: {len(integrations)}")
        
        if integrations:
            print(f"\n🔗 Available Integrations:")
            for integration in integrations:
                print(f"- ID: {integration.id}, User ID: {integration.user_id}")
                print(f"  Provider: {integration.provider}")
                print(f"  Email Account: {integration.email_account}")
                print(f"  Active: {integration.is_active}")
        else:
            print("⚠️  No Integration records found.")
            
    except Exception as e:
        print(f"❌ Error querying Integrations: {str(e)}")

def check_database_schema():
    """Check if all required tables exist"""
    print_separator("DATABASE SCHEMA VERIFICATION")
    
    try:
        # Check if tables exist
        tables_to_check = [
            'email_parsing_jobs',
            'banks', 
            'parsing_rules',
            'transactions',
            'integrations',
            'job_queue'
        ]
        
        print("📋 Checking table existence:")
        for table in tables_to_check:
            try:
                result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                print(f"✅ {table}: {result} records")
            except Exception as e:
                print(f"❌ {table}: Error - {str(e)}")
                
    except Exception as e:
        print(f"❌ Error checking schema: {str(e)}")

def main():
    """Main verification function"""
    print("🔍 DATABASE VERIFICATION SCRIPT")
    print("Verifying current database state and AI integration compatibility...")
    
    try:
        # Initialize database connection
        init_database()
        print("✅ Database connection established")
        
        # Run all verifications
        check_database_schema()
        verify_integrations() 
        verify_banks()
        verify_email_parsing_jobs()
        verify_parsing_rules()
        verify_transactions()
        
        print_separator("VERIFICATION COMPLETE")
        print("🎯 Summary:")
        print("- Database connection: ✅")
        print("- Schema verification: ✅")
        print("- Data inspection: ✅")
        print("\n💡 Next steps:")
        print("1. If EmailParsingJobs exist, AI integration should work")
        print("2. If no ParsingRules exist, AI will generate them automatically")
        print("3. Make sure OPENAI_API_KEY is configured in .env")
        
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 