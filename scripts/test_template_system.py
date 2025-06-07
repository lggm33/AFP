#!/usr/bin/env python3
"""
Test script for the new Bank Email Template System.
This script will test template generation, matching, and extraction.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import init_database
from app.models.bank import Bank
from app.models.email_parsing_job import EmailParsingJob
from app.models.bank_email_template import BankEmailTemplate
from app.services.bank_template_service import BankTemplateService
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

def main():
    print("🧪 Testing Bank Email Template System")
    print("=" * 50)
    
    # Initialize database
    try:
        init_database()
        print("✅ Database initialized")
    except Exception as e:
        print(f"❌ Database error: {e}")
        return
    
    # Create services
    template_service = BankTemplateService()
    print("✅ Template service initialized")
    
    # Get database session
    from app.core.database import DatabaseSession
    
    with DatabaseSession() as db:
        # 1. Check existing banks and emails
        print("\n📊 Current System Status:")
        banks = db.query(Bank).all()
        print(f"   • Banks: {len(banks)}")
        
        for bank in banks:
            email_count = db.query(EmailParsingJob).filter_by(bank_id=bank.id).count()
            template_count = db.query(BankEmailTemplate).filter_by(bank_id=bank.id).count()
            print(f"   • {bank.name}: {email_count} emails, {template_count} templates")
        
        # 2. Test template generation for each bank
        print("\n🤖 Testing Template Generation:")
        
        for bank in banks:
            print(f"\n--- Testing {bank.name} ---")
            
            # Get sample emails
            sample_emails = db.query(EmailParsingJob).filter_by(
                bank_id=bank.id
            ).limit(3).all()
            
            if not sample_emails:
                print(f"   ⚠️  No emails found for {bank.name}")
                continue
            
            print(f"   📧 Found {len(sample_emails)} sample emails")
            
            # Check existing templates
            existing_templates = template_service.get_templates_for_bank(bank.id)
            print(f"   📋 Existing templates: {len(existing_templates)}")
            
            if not existing_templates:
                print(f"   🔄 Generating new template for {bank.name}...")
                try:
                    new_template = template_service.auto_generate_template(
                        bank.id,
                        sample_emails
                    )
                    
                    if new_template:
                        print(f"   ✅ Generated: '{new_template.template_name}' (Type: {new_template.template_type})")
                        print(f"      Amount Pattern: {new_template.amount_regex[:100]}...")
                        
                        # Test the template with sample emails
                        test_results = template_service.validate_template(new_template, sample_emails)
                        print(f"      Validation: {test_results['successful_extractions']}/{test_results['total_tested']} successful")
                        print(f"      Avg Confidence: {test_results['avg_confidence']:.2f}")
                        
                        # Show sample extraction
                        if test_results['extraction_samples']:
                            sample = test_results['extraction_samples'][0]
                            print(f"      Sample Extraction: {sample['extraction']['extracted_data']}")
                    else:
                        print(f"   ❌ Failed to generate template")
                        
                except Exception as e:
                    print(f"   ❌ Error generating template: {e}")
            else:
                print(f"   📋 Testing existing templates:")
                # Reload templates to avoid detached instance issues
                fresh_templates = db.query(BankEmailTemplate).filter_by(bank_id=bank.id).all()
                for template in fresh_templates:
                    print(f"      • {template.template_name} (Priority: {template.priority})")
                    
                    # Test template with a sample email
                    if sample_emails:
                        test_email = sample_emails[0]
                        match_score = template.calculate_match_score(
                            test_email.email_subject or '',
                            test_email.email_from or '',
                            test_email.email_body or ''
                        )
                        print(f"        Match Score: {match_score:.2f}")
                        
                        if match_score >= template.confidence_threshold:
                            extraction = template.extract_data(test_email.email_body or '')
                            print(f"        Extraction: {extraction['extracted_data']}")
                            print(f"        Confidence: {extraction['confidence_score']:.2f}")
        
        # 3. Test end-to-end processing
        print("\n🔄 Testing End-to-End Processing:")
        
        # Find an email that hasn't been processed with templates
        unprocessed_email = db.query(EmailParsingJob).filter(
            EmailParsingJob.bank_id.isnot(None),
            EmailParsingJob.status == 'pending'
        ).first()
        
        if unprocessed_email:
            bank = db.query(Bank).get(unprocessed_email.bank_id)
            print(f"   📧 Testing with email from {bank.name}")
            
            # Find best template
            best_template = template_service.find_best_template(
                bank.id,
                unprocessed_email.email_subject or '',
                unprocessed_email.email_from or '',
                unprocessed_email.email_body or ''
            )
            
            if best_template:
                print(f"   ✅ Selected template: '{best_template.template_name}'")
                
                # Extract data
                extraction_result = template_service.extract_transaction_data(
                    best_template,
                    unprocessed_email.email_body or ''
                )
                
                print(f"   💰 Extraction Result:")
                print(f"      Confidence: {extraction_result['confidence_score']:.2f}")
                print(f"      Data: {extraction_result['extracted_data']}")
                
                # Test data cleaning
                from app.workers.transaction_creation_worker import TransactionCreationWorker
                worker = TransactionCreationWorker()
                cleaned_data = worker._clean_template_extraction(extraction_result['extracted_data'])
                
                if cleaned_data:
                    print(f"   ✅ Cleaned Data: {cleaned_data}")
                else:
                    print(f"   ❌ Data cleaning failed")
            else:
                print(f"   ⚠️  No matching template found")
        else:
            print(f"   ⚠️  No unprocessed emails available for testing")
        
        # 4. Performance Summary
        print("\n📈 Template Performance Summary:")
        all_templates = db.query(BankEmailTemplate).all()
        
        total_templates = len(all_templates)
        active_templates = len([t for t in all_templates if t.is_active])
        
        print(f"   • Total Templates: {total_templates}")
        print(f"   • Active Templates: {active_templates}")
        
        if all_templates:
            success_rates = []
            for template in all_templates:
                total_attempts = template.success_count + template.failure_count
                if total_attempts > 0:
                    success_rate = template.success_count / total_attempts
                    success_rates.append(success_rate)
                    print(f"   • {template.template_name}: {success_rate:.1%} success ({template.success_count}/{total_attempts})")
            
            if success_rates:
                avg_success_rate = sum(success_rates) / len(success_rates)
                print(f"   • Average Success Rate: {avg_success_rate:.1%}")
    
    print("\n✅ Template System Test Complete!")
    print("=" * 50)

if __name__ == "__main__":
    main() 