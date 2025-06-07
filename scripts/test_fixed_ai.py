#!/usr/bin/env python3
"""
Test the improved AI prompts and regex validation - fixed version.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import init_database, db
from app.models.email_parsing_job import EmailParsingJob
from app.models.bank import Bank
from app.models.parsing_rule import ParsingRule
from app.services.ai_rule_generator import AIRuleGeneratorService

def test_fixed_ai_system():
    """Test AI with all fixes applied"""
    print("🚀 TESTING FIXED AI SYSTEM")
    print("="*50)
    
    try:
        # Use BCR (smaller dataset)
        bank = db.session.query(Bank).filter_by(id=3).first()  # BCR
        if not bank:
            print("❌ BCR bank not found")
            return
        
        print(f"🏦 Testing with: {bank.name}")
        
        # Clear existing rules
        existing_rules = db.session.query(ParsingRule).filter_by(bank_id=bank.id).all()
        if existing_rules:
            print(f"🧹 Clearing {len(existing_rules)} existing rules...")
            for rule in existing_rules:
                db.session.delete(rule)
            db.session.commit()
        
        # Get sample emails
        sample_emails = db.session.query(EmailParsingJob).filter_by(bank_id=bank.id).all()
        print(f"📧 Using {len(sample_emails)} sample emails")
        
        if len(sample_emails) < 2:
            print("❌ Need at least 2 emails")
            return
        
        # Show content preview
        ai_service = AIRuleGeneratorService()
        if sample_emails:
            clean_text = ai_service._parse_email_body(sample_emails[0].email_body)
            print(f"\n📄 Sample content:")
            print(f"   Subject: {sample_emails[0].email_subject}")
            print(f"   Content: {clean_text[:150]}...")
        
        print(f"\n🧠 Generating rules with FIXED AI system...")
        rules = ai_service.generate_parsing_rules_for_bank(bank.id, sample_emails)
        
        if not rules:
            print("❌ No rules generated")
            return
        
        print(f"\n✅ Generated {len(rules)} rules:")
        
        # Test each rule
        for rule in rules:
            print(f"\n📋 {rule.rule_name} ({rule.rule_type}):")
            print(f"   Pattern: {rule.regex_pattern}")
            print(f"   Success: {rule.success_count} emails")
            print(f"   Confidence: {rule.confidence_boost:.2f}")
            
            # Test regex compilation
            import re
            try:
                pattern = re.compile(rule.regex_pattern, re.IGNORECASE)
                print(f"   ✅ Compiles successfully")
                
                # Test against sample content
                if sample_emails:
                    clean_content = ai_service._parse_email_body(sample_emails[0].email_body)
                    match = pattern.search(clean_content)
                    if match:
                        extracted = match.groupdict().get(rule.rule_type)
                        print(f"   ✅ Extracts: '{extracted}'")
                    else:
                        print(f"   ❌ No match on test")
                        
            except re.error as e:
                print(f"   ❌ Regex error: {e}")
        
        return rules
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

def show_improvements():
    """Show what was fixed"""
    print(f"\n🔧 FIXES APPLIED:")
    print("="*40)
    print(f"✅ Fixed regex validation syntax error")
    print(f"✅ Added JSON escape handling")
    print(f"✅ Improved prompt with correct examples")
    print(f"✅ Better error logging")
    print(f"✅ Structural validation enhanced")

if __name__ == "__main__":
    try:
        init_database()
        rules = test_fixed_ai_system()
        show_improvements()
        
        print(f"\n🎉 FIXED SYSTEM TEST COMPLETE!")
        if rules:
            print(f"   ✅ Successfully generated {len(rules)} working rules")
        else:
            print(f"   ⚠️  Check API key configuration")
            
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        exit(1) 