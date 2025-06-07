#!/usr/bin/env python3
"""
Test the enhanced AI system with automatic retry, validation, and scoring.
This script demonstrates the improved regex generation capabilities.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import init_database, db
from app.models.email_parsing_job import EmailParsingJob
from app.models.bank import Bank
from app.models.parsing_rule import ParsingRule
from app.services.ai_rule_generator import AIRuleGeneratorService
import json

def test_enhanced_ai_system():
    """Test the enhanced AI system with a specific bank"""
    print("🤖 TESTING ENHANCED AI SYSTEM WITH RETRY & VALIDATION")
    print("="*70)
    
    try:
        # Select a bank to test
        banks = db.session.query(Bank).all()
        print(f"📊 Available banks:")
        for bank in banks:
            email_count = db.session.query(EmailParsingJob).filter_by(bank_id=bank.id).count()
            rule_count = db.session.query(ParsingRule).filter_by(bank_id=bank.id).count()
            print(f"   - {bank.name} (ID: {bank.id}): {email_count} emails, {rule_count} rules")
        
        # Choose bank with most emails but no rules
        target_bank = None
        for bank in banks:
            email_count = db.session.query(EmailParsingJob).filter_by(bank_id=bank.id).count()
            rule_count = db.session.query(ParsingRule).filter_by(bank_id=bank.id).count()
            
            if email_count > 0:
                target_bank = bank
                break
        
        if not target_bank:
            print("❌ No bank with emails found for testing")
            return
        
        print(f"\n🎯 Testing with: {target_bank.name} (ID: {target_bank.id})")
        
        # Get sample emails
        sample_emails = db.session.query(EmailParsingJob).filter_by(
            bank_id=target_bank.id
        ).limit(5).all()
        
        print(f"📧 Using {len(sample_emails)} sample emails:")
        for i, email in enumerate(sample_emails, 1):
            print(f"   {i}. {email.email_subject[:60]}...")
        
        # Clear existing rules for clean test
        existing_rules = db.session.query(ParsingRule).filter_by(bank_id=target_bank.id).all()
        if existing_rules:
            print(f"\n🧹 Clearing {len(existing_rules)} existing rules for clean test...")
            for rule in existing_rules:
                db.session.delete(rule)
            db.session.commit()
        
        # Initialize enhanced AI service
        print(f"\n🚀 Initializing Enhanced AI Service...")
        ai_service = AIRuleGeneratorService()
        
        print(f"   - Model: {ai_service.model}")
        print(f"   - Max retries: {ai_service.max_retries}")
        print(f"   - Min success rate: {ai_service.min_success_rate}")
        print(f"   - Fallback patterns: {len(ai_service.fallback_patterns)} types")
        
        # Generate rules with enhanced system
        print(f"\n🧠 Generating rules with enhanced AI system...")
        print("   This will automatically:")
        print("   1. Try generating rules with OpenAI")
        print("   2. Validate each rule against sample emails")
        print("   3. Retry with improved prompts if rules fail")
        print("   4. Use fallback patterns as last resort")
        
        rules = ai_service.generate_parsing_rules_for_bank(target_bank.id, sample_emails)
        
        if not rules:
            print("❌ Enhanced AI system failed to generate any working rules")
            return
        
        print(f"\n✅ SUCCESS! Generated {len(rules)} validated rules:")
        
        # Display generated rules with details
        for rule in rules:
            print(f"\n📋 {rule.rule_name} ({rule.rule_type}):")
            print(f"   Pattern: {rule.regex_pattern}")
            print(f"   Generation: {rule.generation_method}")
            print(f"   Created by: {rule.created_by}")
            print(f"   Confidence: {rule.confidence_boost:.2f}")
            print(f"   Success count: {rule.success_count}")
            
            if rule.example_input:
                print(f"   Example input: {rule.example_input[:80]}...")
            if rule.example_output:
                print(f"   Example output: {rule.example_output}")
        
        # Test the rules against emails
        print(f"\n🧪 TESTING GENERATED RULES AGAINST EMAILS:")
        
        for rule in rules[:3]:  # Test first 3 rules
            print(f"\n   Testing '{rule.rule_name}':")
            success_rate, extractions = ai_service.test_rule_against_emails(rule, sample_emails)
            
            print(f"   Success rate: {success_rate:.1%}")
            
            if extractions:
                print(f"   Sample extractions:")
                for extraction in extractions[:2]:
                    print(f"     - '{extraction['extracted']}' from email {extraction['email_id']}")
            else:
                print(f"   No extractions found")
        
        # Summary
        print(f"\n📊 ENHANCED AI SYSTEM SUMMARY:")
        print(f"   🎯 Target Bank: {target_bank.name}")
        print(f"   📧 Sample Emails: {len(sample_emails)}")
        print(f"   📋 Rules Generated: {len(rules)}")
        print(f"   🤖 AI Model Used: {ai_service.model}")
        
        generation_methods = {}
        for rule in rules:
            method = rule.generation_method
            generation_methods[method] = generation_methods.get(method, 0) + 1
        
        print(f"   🔧 Generation Methods:")
        for method, count in generation_methods.items():
            print(f"     - {method}: {count} rules")
        
        avg_confidence = sum(rule.confidence_boost for rule in rules) / len(rules)
        print(f"   📈 Average Confidence: {avg_confidence:.2f}")
        
        print(f"\n🎉 Enhanced AI system successfully generated robust regex patterns!")
        print(f"    The system automatically validated each rule and kept only working ones.")
        
    except Exception as e:
        print(f"❌ Error testing enhanced AI system: {str(e)}")
        import traceback
        traceback.print_exc()

def test_specific_bank_by_id(bank_id: int):
    """Test enhanced AI with a specific bank ID"""
    print(f"🎯 TESTING ENHANCED AI WITH BANK ID: {bank_id}")
    print("="*60)
    
    try:
        bank = db.session.query(Bank).get(bank_id)
        if not bank:
            print(f"❌ Bank with ID {bank_id} not found")
            return
        
        print(f"🏦 Bank: {bank.name}")
        
        # Get sample emails
        sample_emails = db.session.query(EmailParsingJob).filter_by(bank_id=bank_id).all()
        print(f"📧 Available emails: {len(sample_emails)}")
        
        if len(sample_emails) < 2:
            print("❌ Need at least 2 emails for meaningful testing")
            return
        
        # Initialize AI service
        ai_service = AIRuleGeneratorService()
        
        # Generate rules
        rules = ai_service.generate_parsing_rules_for_bank(bank_id, sample_emails)
        
        print(f"✅ Generated {len(rules)} rules for {bank.name}")
        
        for rule in rules:
            print(f"   - {rule.rule_name}: {rule.success_count} matches")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def demonstrate_fallback_system():
    """Demonstrate the fallback pattern system"""
    print("🔧 DEMONSTRATING FALLBACK PATTERN SYSTEM")
    print("="*50)
    
    try:
        ai_service = AIRuleGeneratorService()
        
        print("💡 Available fallback patterns:")
        for rule_type, patterns in ai_service.fallback_patterns.items():
            print(f"\n{rule_type.upper()}:")
            for i, pattern in enumerate(patterns, 1):
                print(f"   {i}. {pattern}")
        
        # Test fallback patterns with sample text
        test_texts = [
            "Transaction amount: $1,234.56",
            "Monto: ₡500,000.00",
            "Date: 2024-01-15",
            "Purchase at WALMART STORE #123",
            "Transfer from BAC to BCR",
            "EUR 45.67 paid to merchant"
        ]
        
        print(f"\n🧪 Testing fallback patterns against sample texts:")
        
        import re
        for text in test_texts:
            print(f"\nText: '{text}'")
            
            for rule_type, patterns in ai_service.fallback_patterns.items():
                for pattern in patterns:
                    try:
                        match = re.search(pattern, text, re.IGNORECASE)
                        if match:
                            groups = match.groupdict()
                            if groups.get(rule_type):
                                print(f"   ✅ {rule_type}: '{groups[rule_type]}'")
                                break
                    except:
                        continue
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    try:
        # Initialize database
        init_database()
        
        if len(sys.argv) > 1:
            if sys.argv[1] == "fallback":
                demonstrate_fallback_system()
            elif sys.argv[1].isdigit():
                test_specific_bank_by_id(int(sys.argv[1]))
            else:
                print("Usage: python test_enhanced_ai.py [bank_id|fallback]")
        else:
            test_enhanced_ai_system()
            
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        exit(1) 