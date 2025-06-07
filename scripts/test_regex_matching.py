#!/usr/bin/env python3
"""
Script to test regex patterns from parsing rules against actual email content.
This will help diagnose why emails aren't matching parsing rules.
"""

import sys
import re
sys.path.insert(0, '.')

from app.core.database import init_database, db
from app.models.email_parsing_job import EmailParsingJob
from app.models.bank import Bank
from app.models.parsing_rule import ParsingRule

def test_regex_against_email(email_job: EmailParsingJob, parsing_rule: ParsingRule):
    """Test a specific regex rule against an email"""
    print(f"\n🔍 TESTING RULE: {parsing_rule.rule_name}")
    print(f"   Type: {parsing_rule.rule_type}")
    print(f"   Pattern: {parsing_rule.regex_pattern}")
    print("-" * 60)
    
    try:
        # Test the regex
        match = re.search(parsing_rule.regex_pattern, email_job.email_body, re.MULTILINE | re.IGNORECASE)
        
        if match:
            print("✅ MATCH FOUND!")
            print(f"   Full match: '{match.group(0)}'")
            
            # Show groups if any
            if match.groups():
                print("   Groups:")
                for i, group in enumerate(match.groups(), 1):
                    print(f"     Group {i}: '{group}'")
            
            # Show named groups if any
            if match.groupdict():
                print("   Named groups:")
                for name, value in match.groupdict().items():
                    print(f"     {name}: '{value}'")
        else:
            print("❌ NO MATCH")
            
    except re.error as e:
        print(f"❌ REGEX ERROR: {e}")
    except Exception as e:
        print(f"❌ ERROR: {e}")

def show_email_content(email_job: EmailParsingJob):
    """Show email content for analysis"""
    print(f"\n📧 EMAIL CONTENT (ID: {email_job.id})")
    print("=" * 80)
    print(f"From: {email_job.email_from}")
    print(f"Subject: {email_job.email_subject}")
    print("\nBody:")
    print("-" * 40)
    print(email_job.email_body[:500] + "..." if len(email_job.email_body) > 500 else email_job.email_body)
    print("-" * 40)

def test_bank_rules_against_emails(bank_id: int, limit: int = 3):
    """Test all parsing rules for a bank against sample emails"""
    print(f"\n🏦 TESTING BANK ID: {bank_id}")
    print("=" * 80)
    
    # Get bank
    bank = db.session.query(Bank).filter_by(id=bank_id).first()
    if not bank:
        print(f"❌ Bank {bank_id} not found")
        return
    
    print(f"Bank: {bank.name}")
    
    # Get parsing rules for this bank
    parsing_rules = db.session.query(ParsingRule).filter_by(
        bank_id=bank_id,
        is_active=True
    ).order_by(ParsingRule.priority.desc()).all()
    
    if not parsing_rules:
        print(f"❌ No parsing rules found for {bank.name}")
        return
    
    print(f"Found {len(parsing_rules)} parsing rules")
    
    # Get sample emails for this bank
    email_jobs = db.session.query(EmailParsingJob).filter_by(
        bank_id=bank_id
    ).limit(limit).all()
    
    if not email_jobs:
        print(f"❌ No emails found for {bank.name}")
        return
    
    print(f"Testing against {len(email_jobs)} emails")
    
    # Test each email against each rule
    for email_job in email_jobs:
        show_email_content(email_job)
        
        for parsing_rule in parsing_rules:
            test_regex_against_email(email_job, parsing_rule)
        
        print("\n" + "="*80)

def test_all_banks():
    """Test all banks with their rules and emails"""
    print("🌟 TESTING ALL BANKS")
    print("=" * 80)
    
    banks = db.session.query(Bank).all()
    
    for bank in banks:
        test_bank_rules_against_emails(bank.id, limit=1)  # Test 1 email per bank

def identify_bank_for_email(email_job: EmailParsingJob):
    """Test bank identification logic for an email"""
    print(f"\n🔍 TESTING BANK IDENTIFICATION")
    print("=" * 80)
    print(f"Email from: {email_job.email_from}")
    print(f"Email subject: {email_job.email_subject}")
    
    banks = db.session.query(Bank).filter_by(is_active=True).all()
    
    identified_bank = None
    
    for bank in banks:
        print(f"\n🏦 Testing {bank.name}:")
        print(f"   sender_emails: {bank.sender_emails}")
        print(f"   sender_domains: {bank.sender_domains}")
        
        # Check sender emails
        if bank.sender_emails:
            for email in bank.sender_emails:
                if email.lower() in email_job.email_from.lower():
                    print(f"   ✅ MATCH - sender email: {email}")
                    identified_bank = bank
                    break
                else:
                    print(f"   ❌ No match - sender email: {email}")
        
        # Check sender domains
        if bank.sender_domains:
            for domain in bank.sender_domains:
                if domain.lower() in email_job.email_from.lower():
                    print(f"   ✅ MATCH - sender domain: {domain}")
                    identified_bank = bank
                    break
                else:
                    print(f"   ❌ No match - sender domain: {domain}")
        
        # Check subject for bank name
        if bank.name.lower() in email_job.email_subject.lower():
            print(f"   ✅ MATCH - bank name in subject: {bank.name}")
            identified_bank = bank
    
    if identified_bank:
        print(f"\n🎯 IDENTIFIED BANK: {identified_bank.name} (ID: {identified_bank.id})")
    else:
        print(f"\n❌ NO BANK IDENTIFIED")
    
    return identified_bank

def main():
    print("🔍 REGEX MATCHING DIAGNOSTICS")
    print("=" * 80)
    
    init_database()
    
    # Show available options
    print("Available commands:")
    print("1. test_all_banks() - Test all banks")
    print("2. test_bank_rules_against_emails(bank_id, limit=3) - Test specific bank")
    print("3. identify_bank_for_email(email_job) - Test bank identification")
    print("4. show_email_content(email_job) - Show email details")
    
    # Get some sample data
    banks = db.session.query(Bank).all()
    email_jobs = db.session.query(EmailParsingJob).limit(5).all()
    
    print(f"\nAvailable banks: {len(banks)}")
    for bank in banks:
        print(f"  - {bank.name} (ID: {bank.id})")
    
    print(f"\nAvailable emails: {len(email_jobs)}")
    for email in email_jobs[:3]:
        print(f"  - Email {email.id}: From {email.email_from} - {email.email_subject[:50]}...")
    
    # Run basic test
    print("\n" + "="*80)
    print("🚀 RUNNING AUTOMATIC TESTS")
    
    # Test bank identification for first email
    if email_jobs:
        first_email = email_jobs[0]
        identified_bank = identify_bank_for_email(first_email)
        
        if identified_bank:
            # Test rules for this bank
            test_bank_rules_against_emails(identified_bank.id, limit=1)

if __name__ == "__main__":
    main() 