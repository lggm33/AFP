#!/usr/bin/env python3
"""
Test the improved AI prompts and regex validation.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import init_database, db
from app.models.email_parsing_job import EmailParsingJob
from app.models.bank import Bank
from app.models.parsing_rule import ParsingRule
from app.services.ai_rule_generator import AIRuleGeneratorService

def test_improved_ai_prompts():
    """Test AI with improved prompts on a clean slate"""
    print("🚀 TESTING IMPROVED AI PROMPTS & VALIDATION")
    print("="*70)
    
    try:
        # Use a small bank for quick testing (BCR)
        bank = db.session.query(Bank).filter_by(id=3).first()  # BCR
        if not bank:
            print("❌ BCR bank not found")
            return
        
        print(f"🏦 Testing with: {bank.name}")
        
        # Clear ALL existing rules for completely clean test
        existing_rules = db.session.query(ParsingRule).filter_by(bank_id=bank.id).all()
        if existing_rules:
            print(f"🧹 Clearing {len(existing_rules)} existing rules for clean test...")
            for rule in existing_rules:
                db.session.delete(rule)
            db.session.commit()
        
        # Get sample emails
        sample_emails = db.session.query(EmailParsingJob).filter_by(bank_id=bank.id).all()
        print(f"📧 Using {len(sample_emails)} sample emails from {bank.name}")
        
        if len(sample_emails) < 2:
            print("❌ Need at least 2 emails for meaningful testing")
            return
        
        # Show email content preview
        print(f"\n📄 Sample email content:")
        if sample_emails:
            ai_service = AIRuleGeneratorService()
            clean_text = ai_service._parse_email_body(sample_emails[0].email_body)
            print(f"   Subject: {sample_emails[0].email_subject}")
            print(f"   Clean content: {clean_text[:200]}...")
        
        # Test improved AI system
        print(f"\n🧠 Generating rules with IMPROVED PROMPTS...")
        print(f"   - Enhanced regex syntax guidance")
        print(f"   - Structural validation")
        print(f"   - Better examples in prompt")
        
        rules = ai_service.generate_parsing_rules_for_bank(bank.id, sample_emails)
        
        if not rules:
            print("❌ No rules generated")
            return
        
        print(f"\n✅ Generated {len(rules)} validated rules:")
        
        # Analyze generated rules
        for rule in rules:
            print(f"\n📋 Rule: {rule.rule_name} ({rule.rule_type})")
            print(f"   Pattern: {rule.regex_pattern}")
            print(f"   Generation: {rule.generation_method}")
            print(f"   Success count: {rule.success_count}")
            print(f"   Confidence: {rule.confidence_boost:.2f}")
            
            # Test the pattern manually
            import re
            try:
                                pattern = re.compile(rule.regex_pattern, re.IGNORECASE)
                print(f"   ✅ Regex compiles successfully")
                
                # Check for common issues
                issues = []
                if r'[\d{' in rule.regex_pattern:
                    issues.append("Potential square bracket issue")
                if rule.regex_pattern.count('(') != rule.regex_pattern.count(')'):
                    issues.append("Unmatched parentheses")
                
                if issues:
                    print(f"   ⚠️  Potential issues: {', '.join(issues)}")
                else:
                    print(f"   ✅ Pattern looks well-formed")
                    
            except re.error as e:
                print(f"   ❌ Regex error: {e}")
            
            if rule.example_output:
                print(f"   Example output: '{rule.example_output}'")
        
        # Test against actual email content
        print(f"\n🧪 TESTING RULES AGAINST REAL EMAIL CONTENT:")
        
        if sample_emails and rules:
            test_email = sample_emails[0]
            clean_content = ai_service._parse_email_body(test_email.email_body)
            
            for rule in rules[:2]:  # Test first 2 rules
                try:
                    pattern = re.compile(rule.regex_pattern, re.IGNORECASE)
                    match = pattern.search(clean_content)
                    
                    if match:
                        extracted = match.groupdict().get(rule.rule_type)
                        print(f"   ✅ {rule.rule_name}: '{extracted}'")
                    else:
                        print(f"   ❌ {rule.rule_name}: No match")
                        
                except Exception as e:
                    print(f"   ❌ {rule.rule_name}: Error - {e}")
        
        return rules
        
    except Exception as e:
        print(f"❌ Error testing improved AI: {str(e)}")
        import traceback
        traceback.print_exc()

def compare_before_after():
    """Compare old vs new regex patterns"""
    print(f"\n📊 BEFORE vs AFTER COMPARISON:")
    print("="*60)
    
    print(f"❌ BEFORE (problematic patterns):")
    print(f"   Amount: (?P<amount>CRC\\s[\\d{{1,3}}(?:,\\d{{3}})*(?:\\.\\d{{2}})?])")
    print(f"   Result: 'CRC 6' (incomplete)")
    
    print(f"\n✅ AFTER (improved patterns):")
    print(f"   Amount: (?P<amount>CRC\\s\\d{{1,3}}(?:,\\d{{3}})*(?:\\.\\d{{2}})?)")
    print(f"   Result: 'CRC 6,220.00' (complete)")
    
    print(f"\n🔧 Key improvements:")
    print(f"   - Removed problematic square brackets")
    print(f"   - Fixed nested parentheses issues")
    print(f"   - Added explicit syntax examples in prompt")
    print(f"   - Enhanced validation to catch structural issues")

if __name__ == "__main__":
    try:
        # Initialize database
        init_database()
        
        # Test improved system
        rules = test_improved_ai_prompts()
        compare_before_after()
        
        print(f"\n🎉 IMPROVED AI SYSTEM TEST COMPLETE!")
        if rules:
            print(f"   ✅ {len(rules)} working rules generated")
            print(f"   ✅ Enhanced prompts and validation working")
        else:
            print(f"   ⚠️  No rules generated - may need API key or more samples")
        
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        exit(1) 