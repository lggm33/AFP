#!/usr/bin/env python3
"""
Simple test to create transactions from AI-generated rules.
Uses specific email IDs to avoid complex queries.
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

def test_specific_email(email_id: int):
    """Test transaction creation with a specific email"""
    print(f"🔄 TESTING EMAIL ID: {email_id}")
    print("="*50)
    
    try:
        # Get email directly
        email_job = db.session.query(EmailParsingJob).filter_by(id=email_id).first()
        if not email_job:
            print(f"❌ Email {email_id} not found")
            return None
        
        print(f"📧 Email: {email_job.email_subject}")
        print(f"   From: {email_job.email_from}")
        print(f"   Bank ID: {email_job.bank_id}")
        
        # Get bank directly
        bank = db.session.query(Bank).filter_by(id=email_job.bank_id).first()
        if not bank:
            print(f"❌ Bank {email_job.bank_id} not found")
            return None
        
        print(f"🏦 Bank: {bank.name}")
        
        # Get parsing rules directly
        parsing_rules = db.session.query(ParsingRule).filter_by(bank_id=bank.id).all()
        if not parsing_rules:
            print(f"❌ No parsing rules for {bank.name}")
            return None
        
        print(f"📋 Found {len(parsing_rules)} parsing rules")
        
        # Extract data from email
        extracted_data = {}
        email_body = email_job.email_body
        
        for rule in parsing_rules:
            print(f"\n🔍 Testing rule: {rule.rule_name} ({rule.rule_type})")
            print(f"   Pattern: {rule.regex_pattern[:60]}...")
            
            try:
                pattern = re.compile(rule.regex_pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                match = pattern.search(email_body)
                
                if match:
                    groups = match.groupdict()
                    if groups:
                        # Use named group if available
                        value = groups.get(rule.rule_type, match.group(0))
                    else:
                        # Use full match if no named groups
                        value = match.group(0)
                    
                    extracted_data[rule.rule_type] = value
                    print(f"   ✅ Extracted: {value}")
                else:
                    print(f"   ❌ No match")
                    
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
        
        if not extracted_data:
            print("❌ No data extracted")
            return None
        
        print(f"\n🎯 EXTRACTED DATA:")
        for key, value in extracted_data.items():
            print(f"   {key}: {value}")
        
        # Clean and prepare data for transaction
        cleaned_data = {}
        
        # Process amount
        if 'amount' in extracted_data:
            amount_str = extracted_data['amount']
            # Extract numbers from amount string
            numbers = re.findall(r'[\d,]+\.?\d*', amount_str)
            if numbers:
                try:
                    amount_clean = numbers[0].replace(',', '')
                    cleaned_data['amount'] = float(amount_clean)
                except ValueError:
                    cleaned_data['amount'] = 0.0
            else:
                cleaned_data['amount'] = 0.0
        else:
            cleaned_data['amount'] = 0.0
        
        # Process date
        if 'date' in extracted_data:
            date_str = extracted_data['date']
            # Try to extract date
            date_match = re.search(r'(\d{2})/(\d{2})/(\d{4})', date_str)
            if date_match:
                day, month, year = date_match.groups()
                try:
                    cleaned_data['date'] = datetime(int(year), int(month), int(day)).date()
                except ValueError:
                    cleaned_data['date'] = datetime.now().date()
            else:
                cleaned_data['date'] = datetime.now().date()
        else:
            cleaned_data['date'] = datetime.now().date()
        
        # Process description
        if 'description' in extracted_data:
            desc = extracted_data['description']
            desc = desc.replace('transacción realizada en ', '').strip()
            cleaned_data['description'] = desc[:100]
        else:
            cleaned_data['description'] = 'AI Extracted Transaction'
        
        # Process other fields
        cleaned_data['source'] = extracted_data.get('source', f'{bank.name} Email')[:50]
        cleaned_data['from_bank'] = extracted_data.get('from_bank', bank.name)[:50]
        cleaned_data['to_bank'] = extracted_data.get('to_bank', '')[:50] if extracted_data.get('to_bank') else None
        
        print(f"\n🧹 CLEANED DATA:")
        for key, value in cleaned_data.items():
            print(f"   {key}: {value}")
        
        # Create transaction
        transaction = Transaction(
            amount=cleaned_data['amount'],
            date=cleaned_data['date'],
            description=cleaned_data['description'],
            source=cleaned_data['source'],
            from_bank=cleaned_data['from_bank'],
            to_bank=cleaned_data['to_bank'],
            email_parsing_job_id=email_job.id,
            confidence_score=0.8,  # AI extraction confidence
            verification_status='auto',
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        
        # Save transaction
        db.session.add(transaction)
        db.session.commit()
        
        print(f"\n🎉 SUCCESS! Transaction created:")
        print(f"   ID: {transaction.id}")
        print(f"   Amount: {transaction.amount}")
        print(f"   Date: {transaction.date}")
        print(f"   Description: {transaction.description}")
        print(f"   Bank: {bank.name}")
        
        return transaction
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return None

def test_bac_email():
    """Test with a BAC email"""
    print("🏦 TESTING BAC COSTA RICA EMAIL")
    print("="*60)
    
    # Use BAC email ID (should be around 1-9)
    return test_specific_email(1)

def test_scotiabank_email():
    """Test with a Scotiabank email"""
    print("\n🏦 TESTING SCOTIABANK COSTA RICA EMAIL")
    print("="*60)
    
    # Use Scotiabank email ID (should be around 10+)
    return test_specific_email(10)

def show_created_transactions():
    """Show all created transactions"""
    print("\n📊 CREATED TRANSACTIONS SUMMARY")
    print("="*60)
    
    try:
        transactions = db.session.query(Transaction).all()
        print(f"Total transactions: {len(transactions)}")
        
        for transaction in transactions:
            print(f"\n💰 Transaction {transaction.id}:")
            print(f"   Amount: {transaction.amount}")
            print(f"   Date: {transaction.date}")
            print(f"   Description: {transaction.description}")
            print(f"   Source: {transaction.source}")
            print(f"   From Bank: {transaction.from_bank}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def main():
    """Main function"""
    try:
        init_database()
        print("✅ Database initialized")
        
        # Test BAC transaction creation
        bac_transaction = test_bac_email()
        
        # Test Scotiabank transaction creation  
        scotia_transaction = test_scotiabank_email()
        
        # Show results
        show_created_transactions()
        
        # Summary
        print("\n🎯 SUMMARY:")
        print(f"   BAC Transaction: {'✅ Created' if bac_transaction else '❌ Failed'}")
        print(f"   Scotiabank Transaction: {'✅ Created' if scotia_transaction else '❌ Failed'}")
        
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 