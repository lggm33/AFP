#!/usr/bin/env python3
"""
Script to test AI integration directly with a specific email.
This bypasses the workers to test OpenAI functionality directly.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import init_database, db
from app.models.email_parsing_job import EmailParsingJob
from app.models.bank import Bank
from app.models.parsing_rule import ParsingRule
from app.models.transaction import Transaction
from app.services.ai_rule_generator import AIRuleGeneratorService
import json

def test_ai_with_email(email_id=None):
    """Test AI with a specific email"""
    print("🤖 TESTING AI INTEGRATION DIRECTLY")
    print("="*60)
    
    try:
        # Get an email to test
        if email_id:
            email_job = db.session.query(EmailParsingJob).filter_by(id=email_id).first()
        else:
            # Get first BAC email (these have nice structured HTML)
            email_job = db.session.query(EmailParsingJob).filter_by(bank_id=1).first()
        
        if not email_job:
            print("❌ No email found to test")
            return
        
        print(f"📧 Testing with EmailParsingJob ID: {email_job.id}")
        print(f"   From: {email_job.email_from}")
        print(f"   Subject: {email_job.email_subject}")
        print(f"   Bank ID: {email_job.bank_id}")
        
        # Get the bank
        bank = db.session.query(Bank).filter_by(id=email_job.bank_id).first()
        print(f"🏦 Bank: {bank.name} (ID: {bank.id})")
        
        # Check if parsing rules exist for this bank
        existing_rules = db.session.query(ParsingRule).filter_by(bank_id=bank.id).all()
        print(f"📋 Existing parsing rules for {bank.name}: {len(existing_rules)}")
        
        if existing_rules:
            print("✅ Bank already has parsing rules, skipping AI generation")
            for rule in existing_rules:
                print(f"   - Rule ID: {rule.id}, Name: {rule.rule_name}, Type: {rule.rule_type}")
            return
        
        # Initialize AI service
        print("\n🤖 Initializing AI Rule Generator...")
        ai_service = AIRuleGeneratorService()
        
        # Test if OpenAI API key is configured
        try:
            from openai import OpenAI
            import openai
            client = OpenAI()
            print("✅ OpenAI client initialized successfully")
        except Exception as e:
            print(f"❌ OpenAI client initialization failed: {str(e)}")
            return
        
        # Get sample emails for this bank
        sample_emails = db.session.query(EmailParsingJob).filter_by(bank_id=bank.id).limit(3).all()
        print(f"📧 Using {len(sample_emails)} sample emails for AI training")
        
        # Generate parsing rules with AI
        print("\n🧠 Generating parsing rules with AI...")
        rules = ai_service.generate_parsing_rules_for_bank(bank.id, sample_emails)
        
        if not rules:
            print("❌ AI failed to generate parsing rules")
            return
        
        print(f"✅ AI generated {len(rules)} parsing rules:")
        for rule in rules:
            print(f"   📋 {rule.rule_name} ({rule.rule_type}): {rule.regex_pattern[:50]}...")
        
        # Test the first rule against the email
        print("\n🧪 Testing generated rules against email...")
        for rule in rules[:3]:  # Test first 3 rules
            print(f"\n   Testing rule for '{rule.rule_name}' ({rule.rule_type}):")
            print(f"   Pattern: {rule.regex_pattern}")
            
            # Test regex against email content
            import re
            matches = re.findall(rule.regex_pattern, email_job.email_body, re.IGNORECASE | re.DOTALL)
            if matches:
                print(f"   ✅ Match found: {matches[0] if isinstance(matches[0], str) else matches[0]}")
            else:
                print(f"   ❌ No match found")
        
        # Show AI metadata
        first_rule = rules[0] if rules else None
        if first_rule:
            print(f"\n🤖 AI Metadata:")
            print(f"   Model used: {first_rule.ai_model_used}")
            print(f"   Generation method: {first_rule.generation_method}")
            print(f"   Training samples: {len(first_rule.training_emails_sample)}")
        
        print(f"\n🎯 SUCCESS! AI successfully generated {len(rules)} parsing rules for {bank.name}")
        
    except Exception as e:
        print(f"❌ Error testing AI: {str(e)}")
        import traceback
        traceback.print_exc()

def list_available_emails():
    """List available emails for testing"""
    print("📧 AVAILABLE EMAILS FOR TESTING")
    print("="*60)
    
    try:
        banks = db.session.query(Bank).all()
        
        for bank in banks:
            print(f"\n🏦 {bank.name} (ID: {bank.id})")
            
            emails = db.session.query(EmailParsingJob).filter_by(bank_id=bank.id).limit(3).all()
            for email in emails:
                print(f"   📧 ID: {email.id} - {email.email_subject[:60]}...")
            
            total_count = db.session.query(EmailParsingJob).filter_by(bank_id=bank.id).count()
            print(f"   Total emails: {total_count}")
    
    except Exception as e:
        print(f"❌ Error listing emails: {str(e)}")

def main():
    """Main function"""
    try:
        # Initialize database
        init_database()
        print("✅ Database connection established")
        
        # List available emails
        list_available_emails()
        
        # Test AI with BAC email (bank_id=1)
        print("\n" + "="*60)
        test_ai_with_email()
        
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 