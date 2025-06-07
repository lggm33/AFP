#!/usr/bin/env python3
"""
Test AI with Scotiabank emails specifically
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import init_database, db
from app.models.email_parsing_job import EmailParsingJob
from app.models.bank import Bank
from app.models.parsing_rule import ParsingRule
from app.services.ai_rule_generator import AIRuleGeneratorService

def test_scotiabank_ai():
    """Test AI with Scotiabank emails"""
    print("🏦 TESTING AI WITH SCOTIABANK EMAILS")
    print("="*60)
    
    try:
        # Get Scotiabank (ID: 2)
        bank = db.session.query(Bank).filter_by(id=2).first()
        if not bank:
            print("❌ Scotiabank not found")
            return
        
        print(f"🏦 Bank: {bank.name} (ID: {bank.id})")
        
        # Get sample emails
        sample_emails = db.session.query(EmailParsingJob).filter_by(bank_id=bank.id).limit(3).all()
        print(f"📧 Found {len(sample_emails)} sample emails")
        
        for email in sample_emails:
            print(f"   - {email.email_subject[:60]}...")
        
        # Check existing rules
        existing_rules = db.session.query(ParsingRule).filter_by(bank_id=bank.id).all()
        print(f"📋 Existing rules: {len(existing_rules)}")
        
        if existing_rules:
            print("✅ Rules already exist:")
            for rule in existing_rules:
                print(f"   - {rule.rule_name} ({rule.rule_type})")
            return
        
        # Generate AI rules
        print("\n🤖 Generating AI rules for Scotiabank...")
        ai_service = AIRuleGeneratorService()
        rules = ai_service.generate_parsing_rules_for_bank(bank.id, sample_emails)
        
        print(f"✅ Generated {len(rules)} rules:")
        for rule in rules:
            print(f"   📋 {rule.rule_name} ({rule.rule_type})")
            print(f"      Pattern: {rule.regex_pattern[:80]}...")
            print(f"      Description: {rule.description}")
            print()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    init_database()
    test_scotiabank_ai()

if __name__ == "__main__":
    main() 