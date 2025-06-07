#!/usr/bin/env python3
"""
Script to manually test the complete email processing pipeline
without relying on workers. This will help diagnose regex issues.
"""

import sys
import re
sys.path.insert(0, '.')

from app.core.database import init_database, db
from app.models.email_parsing_job import EmailParsingJob
from app.models.bank import Bank
from app.models.parsing_rule import ParsingRule

def identify_bank_manually(email_from: str, email_subject: str):
    """Manually identify bank using the same logic as TransactionCreationWorker"""
    print(f"\n🔍 MANUAL BANK IDENTIFICATION")
    print("=" * 60)
    print(f"Email from: {email_from}")
    print(f"Email subject: {email_subject}")
    
    banks = db.session.query(Bank).filter_by(is_active=True).all()
    
    for bank in banks:
        print(f"\n🏦 Testing {bank.name}:")
        
        # Check sender emails
        if bank.sender_emails:
            for email in bank.sender_emails:
                if email.lower() in email_from.lower():
                    print(f"   ✅ MATCH - sender email: {email}")
                    return bank
                else:
                    print(f"   ❌ No match - sender email: {email}")
        
        # Check sender domains
        if bank.sender_domains:
            for domain in bank.sender_domains:
                if domain.lower() in email_from.lower():
                    print(f"   ✅ MATCH - sender domain: {domain}")
                    return bank
                else:
                    print(f"   ❌ No match - sender domain: {domain}")
        
        # Check subject for bank name
        if bank.name.lower() in email_subject.lower():
            print(f"   ✅ MATCH - bank name in subject: {bank.name}")
            return bank
    
    print(f"\n❌ NO BANK IDENTIFIED")
    return None

def test_parsing_rules_manually(email_body: str, bank: Bank):
    """Manually test parsing rules against email body"""
    print(f"\n📋 TESTING PARSING RULES FOR {bank.name}")
    print("=" * 60)
    
    parsing_rules = db.session.query(ParsingRule).filter_by(
        bank_id=bank.id,
        is_active=True
    ).order_by(ParsingRule.priority.desc()).all()
    
    if not parsing_rules:
        print(f"❌ No parsing rules found for {bank.name}")
        return None
    
    print(f"Found {len(parsing_rules)} parsing rules")
    
    successful_extractions = []
    
    for rule in parsing_rules:
        print(f"\n🔍 TESTING RULE: {rule.rule_name}")
        print(f"   Type: {rule.rule_type}")
        print(f"   Pattern: {rule.regex_pattern}")
        print(f"   Priority: {rule.priority}")
        print("-" * 40)
        
        try:
            match = re.search(rule.regex_pattern, email_body, re.MULTILINE | re.IGNORECASE)
            
            if match:
                print("✅ MATCH FOUND!")
                print(f"   Full match: '{match.group(0)}'")
                
                if match.groups():
                    print("   Groups:")
                    for i, group in enumerate(match.groups(), 1):
                        print(f"     Group {i}: '{group}'")
                
                if match.groupdict():
                    print("   Named groups:")
                    for name, value in match.groupdict().items():
                        print(f"     {name}: '{value}'")
                
                successful_extractions.append({
                    'rule': rule,
                    'match': match,
                    'groups': match.groupdict()
                })
            else:
                print("❌ NO MATCH")
                
        except re.error as e:
            print(f"❌ REGEX ERROR: {e}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    return successful_extractions

def process_email_manually(email_id: int):
    """Manually process a specific email through the complete pipeline"""
    print(f"\n🚀 MANUAL EMAIL PROCESSING")
    print("=" * 80)
    
    # Get email
    email_job = db.session.query(EmailParsingJob).filter_by(id=email_id).first()
    if not email_job:
        print(f"❌ Email {email_id} not found")
        return
    
    print(f"📧 Processing Email ID: {email_id}")
    print(f"   From: {email_job.email_from}")
    print(f"   Subject: {email_job.email_subject}")
    print(f"   Current bank_id: {email_job.bank_id}")
    
    # Show email body (truncated)
    print(f"\n📄 EMAIL BODY (first 300 chars):")
    print("-" * 40)
    body_preview = email_job.email_body[:300] + "..." if len(email_job.email_body) > 300 else email_job.email_body
    print(body_preview)
    print("-" * 40)
    
    # Step 1: Identify bank
    bank = identify_bank_manually(email_job.email_from, email_job.email_subject)
    
    if not bank:
        print(f"\n❌ FAILED: Could not identify bank")
        return
    
    print(f"\n✅ Bank identified: {bank.name} (ID: {bank.id})")
    
    # Step 2: Test parsing rules
    successful_extractions = test_parsing_rules_manually(email_job.email_body, bank)
    
    if not successful_extractions:
        print(f"\n❌ FAILED: No parsing rules matched")
        return
    
    print(f"\n✅ SUCCESS: {len(successful_extractions)} rules matched")
    
    # Step 3: Show what would be extracted
    print(f"\n💰 EXTRACTION RESULTS:")
    print("=" * 60)
    
    for extraction in successful_extractions:
        rule = extraction['rule']
        groups = extraction['groups']
        
        print(f"\nRule: {rule.rule_name} ({rule.rule_type})")
        if groups:
            for name, value in groups.items():
                print(f"   {name}: {value}")
        else:
            print(f"   Match: {extraction['match'].group(0)}")
    
    return successful_extractions

def main():
    print("🧪 MANUAL EMAIL PROCESSING TEST")
    print("=" * 80)
    
    init_database()
    
    # Get available emails
    emails = db.session.query(EmailParsingJob).limit(5).all()
    
    print("Available emails:")
    for email in emails:
        print(f"  - Email {email.id}: From {email.email_from} - {email.email_subject[:50]}...")
    
    if emails:
        print(f"\n🚀 TESTING FIRST EMAIL (ID: {emails[0].id})")
        process_email_manually(emails[0].id)
        
        # Also test a Scotia email if available
        scotia_email = None
        for email in emails:
            if "scotiabank" in email.email_from.lower():
                scotia_email = email
                break
        
        if scotia_email:
            print(f"\n" + "="*80)
            print(f"🚀 TESTING SCOTIA EMAIL (ID: {scotia_email.id})")
            process_email_manually(scotia_email.id)

if __name__ == "__main__":
    main() 