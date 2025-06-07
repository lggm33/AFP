#!/usr/bin/env python3
"""
Test that AI-generated regex patterns can successfully create transactions.
This tests the complete flow: Email → AI Rules → Data Extraction → Transaction Creation.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import init_database, db
from app.models.email_parsing_job import EmailParsingJob
from app.models.bank import Bank
from app.models.parsing_rule import ParsingRule
from app.models.transaction import Transaction
from datetime import datetime, UTC
import re
import json

def extract_data_with_rules(email_body: str, parsing_rules: list) -> dict:
    """Extract transaction data using AI-generated parsing rules"""
    print("🔍 EXTRACTING DATA WITH AI RULES")
    print("="*50)
    
    extracted_data = {}
    
    for rule in parsing_rules:
        print(f"\n📋 Testing rule: {rule.rule_name} ({rule.rule_type})")
        print(f"   Pattern: {rule.regex_pattern}")
        
        try:
            # Compile regex pattern
            pattern = re.compile(rule.regex_pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            
            # Search for matches
            match = pattern.search(email_body)
            
            if match:
                # Extract named groups
                groups = match.groupdict()
                print(f"   ✅ Match found: {groups}")
                
                # Store extracted value for this field type
                extracted_data[rule.rule_type] = groups.get(rule.rule_type, match.group(0))
                
            else:
                print(f"   ❌ No match found")
                
        except re.error as e:
            print(f"   ❌ Regex error: {str(e)}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    print(f"\n🎯 EXTRACTED DATA SUMMARY:")
    for field_type, value in extracted_data.items():
        print(f"   {field_type}: {value}")
    
    return extracted_data

def clean_extracted_data(extracted_data: dict) -> dict:
    """Clean and format extracted data for transaction creation"""
    print("\n🧹 CLEANING EXTRACTED DATA")
    print("="*50)
    
    cleaned_data = {}
    
    # Clean amount
    if 'amount' in extracted_data:
        amount_str = extracted_data['amount']
        print(f"   Raw amount: {amount_str}")
        
        # Remove currency symbols and text, extract numbers
        import re
        numbers = re.findall(r'[\d,]+\.?\d*', amount_str)
        if numbers:
            # Take the largest number (usually the amount)
            amount_clean = numbers[0].replace(',', '')
            try:
                cleaned_data['amount'] = float(amount_clean)
                print(f"   ✅ Cleaned amount: {cleaned_data['amount']}")
            except ValueError:
                print(f"   ❌ Could not parse amount: {amount_clean}")
    
    # Clean date
    if 'date' in extracted_data:
        date_str = extracted_data['date']
        print(f"   Raw date: {date_str}")
        
        # Extract date components
        date_patterns = [
            r'(\d{2})/(\d{2})/(\d{4})',  # DD/MM/YYYY
            r'(\d{2})-(\d{2})-(\d{4})',  # DD-MM-YYYY
            r'(\d{4})-(\d{2})-(\d{2})'   # YYYY-MM-DD
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_str)
            if match:
                day, month, year = match.groups()
                try:
                    # Assume DD/MM/YYYY format for Costa Rican banks
                    cleaned_data['date'] = datetime(int(year), int(month), int(day)).date()
                    print(f"   ✅ Cleaned date: {cleaned_data['date']}")
                    break
                except ValueError:
                    continue
    
    # Clean description
    if 'description' in extracted_data:
        desc_str = extracted_data['description']
        print(f"   Raw description: {desc_str}")
        
        # Remove common prefixes and clean up
        desc_clean = desc_str.replace('transacción realizada en ', '')
        desc_clean = desc_clean.replace('realizada en ', '')
        desc_clean = desc_clean.strip()
        cleaned_data['description'] = desc_clean[:100]  # Limit length
        print(f"   ✅ Cleaned description: {cleaned_data['description']}")
    
    # Clean source
    if 'source' in extracted_data:
        source_str = extracted_data['source']
        print(f"   Raw source: {source_str}")
        cleaned_data['source'] = source_str[:50]  # Limit length
        print(f"   ✅ Cleaned source: {cleaned_data['source']}")
    
    # Clean bank fields
    for field in ['from_bank', 'to_bank']:
        if field in extracted_data:
            bank_str = extracted_data[field]
            print(f"   Raw {field}: {bank_str}")
            cleaned_data[field] = bank_str[:50]  # Limit length
            print(f"   ✅ Cleaned {field}: {cleaned_data[field]}")
    
    return cleaned_data

def create_transaction_from_data(email_job: EmailParsingJob, bank: Bank, extracted_data: dict) -> Transaction:
    """Create a Transaction object from extracted data"""
    print("\n💰 CREATING TRANSACTION")
    print("="*50)
    
    try:
        # Create transaction with extracted data
        transaction = Transaction(
            # Required fields
            amount=extracted_data.get('amount', 0.0),
            date=extracted_data.get('date', datetime.now().date()),
            description=extracted_data.get('description', 'AI Extracted Transaction'),
            
            # Optional fields
            source=extracted_data.get('source', f'{bank.name} Email'),
            from_bank=extracted_data.get('from_bank', bank.name),
            to_bank=extracted_data.get('to_bank'),
            
            # Metadata
            email_parsing_job_id=email_job.id,
            bank_id=bank.id,
            transaction_type='debit',  # Default, could be extracted
            status='pending',
            
            # Audit fields
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        
        print(f"✅ Transaction created:")
        print(f"   Amount: {transaction.amount}")
        print(f"   Date: {transaction.date}")
        print(f"   Description: {transaction.description}")
        print(f"   Source: {transaction.source}")
        print(f"   From Bank: {transaction.from_bank}")
        print(f"   To Bank: {transaction.to_bank}")
        
        return transaction
        
    except Exception as e:
        print(f"❌ Error creating transaction: {str(e)}")
        raise

def test_email_to_transaction(email_id: int):
    """Test complete flow from email to transaction"""
    print("🔄 TESTING COMPLETE EMAIL → TRANSACTION FLOW")
    print("="*60)
    
    try:
        # Get email
        email_job = db.session.query(EmailParsingJob).filter_by(id=email_id).first()
        if not email_job:
            print(f"❌ Email with ID {email_id} not found")
            return
        
        print(f"📧 Email: {email_job.email_subject}")
        print(f"   From: {email_job.email_from}")
        print(f"   Bank ID: {email_job.bank_id}")
        
        # Get bank and rules
        bank = db.session.query(Bank).filter_by(id=email_job.bank_id).first()
        if not bank:
            print(f"❌ Bank with ID {email_job.bank_id} not found")
            return
        
        print(f"🏦 Bank: {bank.name}")
        
        # Get parsing rules for this bank
        parsing_rules = db.session.query(ParsingRule).filter_by(
            bank_id=bank.id,
            is_active=True
        ).order_by(ParsingRule.priority.desc()).all()
        
        if not parsing_rules:
            print(f"❌ No parsing rules found for {bank.name}")
            return
        
        print(f"📋 Found {len(parsing_rules)} parsing rules")
        
        # Extract data using AI rules
        extracted_data = extract_data_with_rules(email_job.email_body, parsing_rules)
        
        if not extracted_data:
            print("❌ No data extracted from email")
            return
        
        # Clean extracted data
        cleaned_data = clean_extracted_data(extracted_data)
        
        if not cleaned_data:
            print("❌ No data remained after cleaning")
            return
        
        # Create transaction
        transaction = create_transaction_from_data(email_job, bank, cleaned_data)
        
        # Save to database
        db.session.add(transaction)
        db.session.commit()
        
        print(f"\n🎉 SUCCESS! Transaction created with ID: {transaction.id}")
        
        return transaction
        
    except Exception as e:
        print(f"❌ Error in email to transaction flow: {str(e)}")
        db.session.rollback()
        import traceback
        traceback.print_exc()

def test_all_banks():
    """Test transaction creation for all banks with AI rules"""
    print("🌟 TESTING TRANSACTION CREATION FOR ALL BANKS")
    print("="*60)
    
    try:
        # Get banks with parsing rules
        banks_with_rules = db.session.query(Bank).join(ParsingRule).distinct().all()
        
        print(f"Found {len(banks_with_rules)} banks with AI-generated rules")
        
        for bank in banks_with_rules:
            print(f"\n🏦 Testing {bank.name}...")
            
            # Get first email for this bank
            email_job = db.session.query(EmailParsingJob).filter_by(bank_id=bank.id).first()
            
            if email_job:
                print(f"   Using email: {email_job.email_subject[:50]}...")
                test_email_to_transaction(email_job.id)
            else:
                print(f"   ❌ No emails found for {bank.name}")
        
    except Exception as e:
        print(f"❌ Error testing all banks: {str(e)}")

def show_transaction_summary():
    """Show summary of created transactions"""
    print("\n📊 TRANSACTION SUMMARY")
    print("="*50)
    
    try:
        transactions = db.session.query(Transaction).all()
        
        print(f"Total transactions: {len(transactions)}")
        
        for transaction in transactions:
            bank = db.session.query(Bank).filter_by(id=transaction.bank_id).first()
            print(f"\n💰 Transaction {transaction.id}:")
            print(f"   Bank: {bank.name if bank else 'Unknown'}")
            print(f"   Amount: {transaction.amount}")
            print(f"   Date: {transaction.date}")
            print(f"   Description: {transaction.description}")
            print(f"   Source: {transaction.source}")
            
    except Exception as e:
        print(f"❌ Error showing transaction summary: {str(e)}")

def main():
    """Main function"""
    try:
        # Initialize database
        init_database()
        print("✅ Database connection established")
        
        # Test all banks
        test_all_banks()
        
        # Show summary
        show_transaction_summary()
        
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 