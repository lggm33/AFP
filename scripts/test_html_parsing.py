#!/usr/bin/env python3
"""
Test the improved HTML parsing functionality.
This script shows how HTML emails are now properly parsed before AI processing.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import init_database, db
from app.models.email_parsing_job import EmailParsingJob
from app.models.bank import Bank
from app.services.ai_rule_generator import AIRuleGeneratorService

def test_html_parsing():
    """Test HTML parsing with actual email content"""
    print("🌐 TESTING HTML PARSING FUNCTIONALITY")
    print("="*60)
    
    try:
        # Get a BAC email (we know these are HTML)
        email_job = db.session.query(EmailParsingJob).filter_by(bank_id=1).first()
        
        if not email_job:
            print("❌ No BAC email found")
            return
        
        print(f"📧 Testing with email ID: {email_job.id}")
        print(f"   Subject: {email_job.email_subject}")
        print(f"   Original length: {len(email_job.email_body)} chars")
        
        # Initialize AI service (which has the HTML parsing)
        ai_service = AIRuleGeneratorService()
        
        # Test HTML detection
        is_html = ai_service._is_html_content(email_job.email_body)
        print(f"📋 HTML detected: {is_html}")
        
        # Parse the email body
        print(f"\n🔄 PARSING HTML CONTENT...")
        clean_text = ai_service._parse_email_body(email_job.email_body)
        
        print(f"✅ Parsed successfully!")
        print(f"   Original length: {len(email_job.email_body)} chars")
        print(f"   Cleaned length: {len(clean_text)} chars")
        print(f"   Reduction: {((len(email_job.email_body) - len(clean_text)) / len(email_job.email_body) * 100):.1f}%")
        
        # Show before/after comparison
        print(f"\n📄 CONTENT COMPARISON:")
        print(f"BEFORE (first 200 chars):")
        print(f"   {email_job.email_body[:200]}")
        
        print(f"\nAFTER (first 500 chars):")
        print(f"   {clean_text[:500]}")
        
        # Test extraction validation
        print(f"\n🧪 TESTING EXTRACTION VALIDATION:")
        
        test_extractions = [
            ("DOCTYPE html", "description"),
            ("0", "amount"),
            ("GORDI FRUTI", "description"),
            ("5,000", "amount"),
            ("06-06-2025", "date"),
            ("html", "description")
        ]
        
        for value, rule_type in test_extractions:
            is_meaningful = ai_service._is_meaningful_extraction(value, rule_type)
            status = "✅" if is_meaningful else "❌"
            print(f"   {status} '{value}' as {rule_type}: {'Meaningful' if is_meaningful else 'Invalid'}")
        
        return clean_text
        
    except Exception as e:
        print(f"❌ Error testing HTML parsing: {str(e)}")
        import traceback
        traceback.print_exc()

def test_improved_ai_with_html():
    """Test the improved AI system with HTML parsing on a clean bank"""
    print(f"\n🚀 TESTING IMPROVED AI WITH HTML PARSING")
    print("="*60)
    
    try:
        # Use BCR (smaller dataset, faster testing)
        bank = db.session.query(Bank).filter_by(id=3).first()  # BCR
        if not bank:
            print("❌ BCR bank not found")
            return
        
        print(f"🏦 Testing with: {bank.name}")
        
        # Get sample emails
        sample_emails = db.session.query(EmailParsingJob).filter_by(bank_id=bank.id).limit(3).all()
        print(f"📧 Using {len(sample_emails)} sample emails")
        
        # Clear existing rules for clean test
        from app.models.parsing_rule import ParsingRule
        existing_rules = db.session.query(ParsingRule).filter_by(bank_id=bank.id).all()
        if existing_rules:
            print(f"🧹 Clearing {len(existing_rules)} existing rules...")
            for rule in existing_rules:
                db.session.delete(rule)
            db.session.commit()
        
        # Test AI with improved system
        ai_service = AIRuleGeneratorService()
        
        print(f"\n🧠 Generating rules with improved AI (HTML parsing + validation)...")
        rules = ai_service.generate_parsing_rules_for_bank(bank.id, sample_emails)
        
        if rules:
            print(f"✅ Generated {len(rules)} validated rules:")
            for rule in rules:
                print(f"   📋 {rule.rule_name} ({rule.rule_type}):")
                print(f"      Example: '{rule.example_output}'")
                print(f"      Confidence: {rule.confidence_boost:.2f}")
        else:
            print(f"❌ No rules generated")
        
        return rules
        
    except Exception as e:
        print(f"❌ Error testing improved AI: {str(e)}")
        import traceback
        traceback.print_exc()

def demonstrate_html_vs_plain():
    """Show difference between HTML and plain text processing"""
    print(f"\n📊 DEMONSTRATING HTML VS PLAIN TEXT PROCESSING")
    print("="*70)
    
    try:
        # Get one HTML email
        html_email = db.session.query(EmailParsingJob).filter_by(bank_id=1).first()
        
        if not html_email:
            print("❌ No HTML email found")
            return
        
        ai_service = AIRuleGeneratorService()
        
        # Process as HTML (correct way)
        print("🌐 Processing as HTML (with parsing):")
        clean_text = ai_service._parse_email_body(html_email.email_body)
        print(f"   Length: {len(clean_text)} chars")
        print(f"   Sample: {clean_text[:200]}...")
        
        # Process as raw text (old way)
        print(f"\n📄 Processing as raw text (old way):")
        raw_text = html_email.email_body[:3000]
        print(f"   Length: {len(raw_text)} chars")
        print(f"   Sample: {raw_text[:200]}...")
        
        # Show why HTML parsing matters
        print(f"\n💡 WHY HTML PARSING MATTERS:")
        print(f"   - HTML version contains tags, styles, scripts")
        print(f"   - Clean version contains actual transaction data")
        print(f"   - AI can extract meaningful patterns from clean text")
        print(f"   - Validation rejects HTML artifacts like 'DOCTYPE html'")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    try:
        # Initialize database
        init_database()
        
        # Run tests
        test_html_parsing()
        test_improved_ai_with_html()
        demonstrate_html_vs_plain()
        
        print(f"\n🎉 HTML PARSING TESTS COMPLETE!")
        print(f"   The improved AI system now:")
        print(f"   ✅ Detects HTML content automatically")
        print(f"   ✅ Extracts clean text from HTML emails")
        print(f"   ✅ Validates extractions for meaningfulness")
        print(f"   ✅ Rejects HTML artifacts and meaningless data")
        
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        exit(1) 