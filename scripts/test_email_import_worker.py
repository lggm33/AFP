#!/usr/bin/env python3
"""
Script to manually test EmailImportWorker and diagnose email import issues
"""

import os
import sys
import logging
from datetime import datetime, timedelta, UTC

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import init_database, DatabaseSession
from app.models.user import User
from app.models.integration import Integration
from app.models.email_import_job import EmailImportJob
from app.models.job_queue import JobQueue
from app.workers.email_import_worker import EmailImportWorker
from app.infrastructure.email.gmail_client import GmailAPIClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EmailImportTester:
    """Comprehensive tester for EmailImportWorker"""
    
    def __init__(self):
        self.gmail_client = None
        self.test_results = []
    
    def log_test(self, test_name: str, success: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if message:
            print(f"    {message}")
        self.test_results.append((test_name, success, message))
    
    def test_1_database_connection(self) -> bool:
        """Test database connectivity"""
        print("\n🔍 Test 1: Database Connection")
        try:
            init_database()
            with DatabaseSession() as session:
                user_count = session.query(User).count()
                integration_count = session.query(Integration).count()
                job_count = session.query(EmailImportJob).count()
                
            self.log_test("Database Connection", True, 
                         f"Users: {user_count}, Integrations: {integration_count}, Jobs: {job_count}")
            return True
        except Exception as e:
            self.log_test("Database Connection", False, str(e))
            return False
    
    def test_2_gmail_authentication(self) -> bool:
        """Test Gmail API authentication"""
        print("\n🔍 Test 2: Gmail Authentication")
        try:
            self.gmail_client = GmailAPIClient()
            
            # Check for credentials file
            if not os.path.exists('credentials.json'):
                self.log_test("Gmail Credentials", False, "credentials.json not found")
                return False
            
            # Check for token file
            if not os.path.exists('token.json'):
                self.log_test("Gmail Token", False, "token.json not found")
                return False
            
            # Test authentication
            if self.gmail_client.authenticate():
                self.log_test("Gmail Authentication", True, f"Label ID: {self.gmail_client.afp_label_id}")
                return True
            else:
                self.log_test("Gmail Authentication", False, "Authentication failed")
                return False
                
        except Exception as e:
            self.log_test("Gmail Authentication", False, str(e))
            return False
    
    def test_3_gmail_api_connectivity(self) -> bool:
        """Test Gmail API basic functionality"""
        print("\n🔍 Test 3: Gmail API Connectivity")
        try:
            if not self.gmail_client:
                self.log_test("Gmail API Test", False, "No authenticated client")
                return False
            
            # Test basic API call
            results = self.gmail_client.service.users().messages().list(
                userId='me',
                maxResults=1
            ).execute()
            
            total_messages = results.get('resultSizeEstimate', 0)
            self.log_test("Gmail API Connectivity", True, f"Total messages in account: {total_messages}")
            return True
            
        except Exception as e:
            self.log_test("Gmail API Connectivity", False, str(e))
            return False
    
    def test_4_bank_emails_search(self) -> bool:
        """Test searching for bank emails"""
        print("\n🔍 Test 4: Bank Emails Search")
        try:
            if not self.gmail_client:
                self.log_test("Bank Emails Search", False, "No authenticated client")
                return False
            
            # Test different search strategies
            search_strategies = [
                ("All bank senders", self._search_all_bank_senders),
                ("Last 30 days", self._search_last_30_days),
                ("Without AFP label filter", self._search_without_afp_filter),
                ("With financial keywords", self._search_with_keywords)
            ]
            
            all_success = True
            for strategy_name, search_func in search_strategies:
                try:
                    count = search_func()
                    self.log_test(f"Search: {strategy_name}", True, f"Found {count} emails")
                except Exception as e:
                    self.log_test(f"Search: {strategy_name}", False, str(e))
                    all_success = False
            
            return all_success
            
        except Exception as e:
            self.log_test("Bank Emails Search", False, str(e))
            return False
    
    def _search_all_bank_senders(self) -> int:
        """Search emails from all configured bank senders"""
        senders_query = ' OR '.join([f'from:{sender}' for sender in self.gmail_client.bank_senders])
        query = f'({senders_query})'
        
        results = self.gmail_client.service.users().messages().list(
            userId='me',
            q=query,
            maxResults=10
        ).execute()
        
        return len(results.get('messages', []))
    
    def _search_last_30_days(self) -> int:
        """Search emails from last 30 days"""
        date_30_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y/%m/%d')
        query = f'after:{date_30_days_ago}'
        
        results = self.gmail_client.service.users().messages().list(
            userId='me',
            q=query,
            maxResults=10
        ).execute()
        
        return len(results.get('messages', []))
    
    def _search_without_afp_filter(self) -> int:
        """Search bank emails without AFP label filter"""
        senders_query = ' OR '.join([f'from:{sender}' for sender in self.gmail_client.bank_senders])
        # Removed the -label:AFP_Processed filter
        query = f'({senders_query})'
        
        results = self.gmail_client.service.users().messages().list(
            userId='me',
            q=query,
            maxResults=50
        ).execute()
        
        return len(results.get('messages', []))
    
    def _search_with_keywords(self) -> int:
        """Search with financial keywords"""
        keywords = ['transacción', 'compra', 'retiro', 'transferencia', 'pago', 'débito', 'crédito']
        keywords_query = ' OR '.join(keywords)
        query = f'({keywords_query})'
        
        results = self.gmail_client.service.users().messages().list(
            userId='me',
            q=query,
            maxResults=10
        ).execute()
        
        return len(results.get('messages', []))
    
    def test_5_get_bank_emails_method(self) -> bool:
        """Test the get_bank_emails method directly"""
        print("\n🔍 Test 5: get_bank_emails() Method")
        try:
            if not self.gmail_client:
                self.log_test("get_bank_emails Method", False, "No authenticated client")
                return False
            
            # Test different configurations
            test_configs = [
                ("Default settings", {}),
                ("First run (30 days)", {"is_first_run": True}),
                ("Last 7 days", {"since_date": datetime.now() - timedelta(days=7)}),
                ("Max 10 results", {"max_results": 10}),
            ]
            
            all_success = True
            for config_name, kwargs in test_configs:
                try:
                    emails = self.gmail_client.get_bank_emails(**kwargs)
                    self.log_test(f"Config: {config_name}", True, f"Retrieved {len(emails)} emails")
                    
                    # Show sample email info
                    if emails:
                        sample = emails[0]
                        print(f"    Sample email: {sample.get('subject', 'No subject')[:50]}...")
                        print(f"    From: {sample.get('from', 'Unknown')}")
                        print(f"    Date: {sample.get('date', 'No date')}")
                        
                except Exception as e:
                    self.log_test(f"Config: {config_name}", False, str(e))
                    all_success = False
            
            return all_success
            
        except Exception as e:
            self.log_test("get_bank_emails Method", False, str(e))
            return False
    
    def test_6_active_integrations(self) -> bool:
        """Test active integrations in database"""
        print("\n🔍 Test 6: Active Integrations")
        try:
            with DatabaseSession() as session:
                # Get active integrations
                active_integrations = session.query(Integration).filter(
                    Integration.is_active == True
                ).all()
                
                if not active_integrations:
                    self.log_test("Active Integrations", False, "No active integrations found")
                    return False
                
                self.log_test("Active Integrations", True, f"Found {len(active_integrations)}")
                
                # Show integration details
                for i, integration in enumerate(active_integrations):
                    print(f"    {i+1}. User ID: {integration.user_id}")
                    print(f"       Email: {integration.email_account}")
                    print(f"       Provider: {integration.provider}")
                    print(f"       Sync freq: {integration.sync_frequency_minutes}min")
                    print(f"       Has tokens: {bool(integration.access_token and integration.refresh_token)}")
                
                return True
                
        except Exception as e:
            self.log_test("Active Integrations", False, str(e))
            return False
    
    def test_7_email_import_jobs(self) -> bool:
        """Test EmailImportJob records"""
        print("\n🔍 Test 7: EmailImportJob Records")
        try:
            with DatabaseSession() as session:
                # Get recent jobs
                recent_jobs = session.query(EmailImportJob).order_by(
                    EmailImportJob.created_at.desc()
                ).limit(5).all()
                
                if not recent_jobs:
                    self.log_test("EmailImportJob Records", False, "No EmailImportJob records found")
                    return False
                
                self.log_test("EmailImportJob Records", True, f"Found {len(recent_jobs)} recent jobs")
                
                # Show job details
                for i, job in enumerate(recent_jobs):
                    print(f"    {i+1}. Job ID: {job.id}")
                    print(f"       Status: {job.status}")
                    print(f"       Integration ID: {job.integration_id}")
                    print(f"       Created: {job.created_at}")
                    print(f"       Last run: {job.last_run_at}")
                    print(f"       Next run: {job.next_run_at}")
                    if job.error_message:
                        print(f"       Error: {job.error_message}")
                
                return True
                
        except Exception as e:
            self.log_test("EmailImportJob Records", False, str(e))
            return False
    
    def test_8_manual_worker_execution(self) -> bool:
        """Test manual EmailImportWorker execution"""
        print("\n🔍 Test 8: Manual Worker Execution")
        try:
            # Create worker instance
            worker = EmailImportWorker()
            self.log_test("Worker Creation", True, f"Worker ID: {worker.worker_id[:8]}...")
            
            # Try to process one cycle manually
            print("    🔄 Running one worker cycle...")
            worker.process_cycle()
            
            self.log_test("Manual Worker Execution", True, "Worker cycle completed")
            return True
            
        except Exception as e:
            self.log_test("Manual Worker Execution", False, str(e))
            return False
    
    def test_9_worker_process_email_import_method(self) -> bool:
        """Test the worker's _process_email_import method directly"""
        print("\n🔍 Test 9: Worker _process_email_import Method")
        try:
            # Get an active EmailImportJob
            with DatabaseSession() as session:
                email_job = session.query(EmailImportJob).filter(
                    EmailImportJob.status.in_(['pending', 'idle'])
                ).first()
                
                if not email_job:
                    self.log_test("EmailImportJob Available", False, "No pending EmailImportJob found")
                    return False
                
                self.log_test("EmailImportJob Available", True, f"Found job ID: {email_job.id}")
                
                # Create worker instance
                worker = EmailImportWorker()
                
                # Test the _process_email_import method directly
                print(f"    🔄 Testing _process_email_import with job {email_job.id}...")
                
                # Mark job as running temporarily
                original_status = email_job.status
                email_job.status = 'running'
                email_job.started_at = datetime.now(UTC)
                session.commit()
                
                try:
                    # Call the method directly
                    result = worker._process_email_import(email_job)
                    
                    self.log_test("_process_email_import Method", True, 
                                 f"Found {result['emails_found']} emails, processed {result['emails_processed']}")
                    
                    # Show details
                    print(f"    📧 Emails found: {result['emails_found']}")
                    print(f"    ✅ Emails processed: {result['emails_processed']}")
                    
                    # Check if EmailParsingJobs were created
                    parsing_jobs = session.query(EmailParsingJob).filter_by(
                        email_import_job_id=email_job.id
                    ).count()
                    print(f"    📝 EmailParsingJobs created: {parsing_jobs}")
                    
                    return True
                    
                finally:
                    # Restore original status
                    email_job.status = original_status
                    email_job.started_at = None
                    session.commit()
                    
        except Exception as e:
            self.log_test("_process_email_import Method", False, str(e))
            return False
    
    def test_10_worker_timezone_handling(self) -> bool:
        """Test the worker's timezone handling method"""
        print("\n🔍 Test 10: Worker Timezone Handling")
        try:
            worker = EmailImportWorker()
            
            # Test timezone handling
            test_cases = [
                ("None datetime", None),
                ("Naive datetime", datetime(2025, 6, 7, 10, 0, 0)),
                ("UTC datetime", datetime(2025, 6, 7, 10, 0, 0, tzinfo=UTC)),
            ]
            
            all_success = True
            for case_name, test_dt in test_cases:
                try:
                    result = worker._ensure_utc_timezone(test_dt)
                    
                    if test_dt is None:
                        success = result is None
                    else:
                        success = result is not None and result.tzinfo is not None
                    
                    if success:
                        self.log_test(f"Timezone: {case_name}", True, f"Result: {result}")
                    else:
                        self.log_test(f"Timezone: {case_name}", False, f"Unexpected result: {result}")
                        all_success = False
                        
                except Exception as e:
                    self.log_test(f"Timezone: {case_name}", False, str(e))
                    all_success = False
            
            return all_success
            
        except Exception as e:
            self.log_test("Worker Timezone Handling", False, str(e))
            return False
    
    def test_11_worker_gmail_integration(self) -> bool:
        """Test the worker's Gmail client integration"""
        print("\n🔍 Test 11: Worker Gmail Client Integration")
        try:
            # Get an active integration
            with DatabaseSession() as session:
                integration = session.query(Integration).filter_by(is_active=True).first()
                
                if not integration:
                    self.log_test("Active Integration", False, "No active integration found")
                    return False
                
                # Create a mock EmailImportJob
                test_job = EmailImportJob(
                    integration_id=integration.id,
                    status='running',
                    last_run_at=datetime.now(UTC) - timedelta(days=1),  # Yesterday
                    created_at=datetime.now(UTC)
                )
                
                # Don't add to session, just use for testing
                test_job.integration = integration
                
                worker = EmailImportWorker()
                
                # Test Gmail client creation within worker
                gmail_client = GmailAPIClient()
                if not gmail_client.authenticate():
                    self.log_test("Worker Gmail Client", False, "Gmail authentication failed")
                    return False
                
                # Test getting emails with worker's logic
                since_date = worker._ensure_utc_timezone(test_job.last_run_at)
                emails = gmail_client.get_bank_emails(since_date=since_date, max_results=10)
                
                self.log_test("Worker Gmail Integration", True, 
                             f"Retrieved {len(emails)} emails using worker logic")
                
                if emails:
                    sample = emails[0]
                    print(f"    Sample: {sample.get('subject', 'No subject')[:40]}...")
                    print(f"    From: {sample.get('from', 'Unknown')}")
                
                return True
                
        except Exception as e:
            self.log_test("Worker Gmail Integration", False, str(e))
            return False
    
    def run_all_tests(self):
        """Run all diagnostic tests"""
        print("🚀 EmailImportWorker Diagnostic Test Suite")
        print("=" * 60)
        
        tests = [
            self.test_1_database_connection,
            self.test_2_gmail_authentication,
            self.test_3_gmail_api_connectivity,
            self.test_4_bank_emails_search,
            self.test_5_get_bank_emails_method,
            self.test_6_active_integrations,
            self.test_7_email_import_jobs,
            self.test_8_manual_worker_execution,
            self.test_9_worker_process_email_import_method,
            self.test_10_worker_timezone_handling,
            self.test_11_worker_gmail_integration
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                test_name = test.__name__.replace('test_', '').replace('_', ' ').title()
                self.log_test(test_name, False, f"Unexpected error: {str(e)}")
        
        # Final summary
        print("\n" + "=" * 60)
        print("📊 DIAGNOSTIC SUMMARY:")
        
        passed = sum(1 for _, success, _ in self.test_results if success)
        total = len(self.test_results)
        
        for test_name, success, message in self.test_results:
            status = "✅" if success else "❌"
            print(f"   {status} {test_name}")
            if message and not success:
                print(f"      Error: {message}")
        
        print(f"\n🎯 Tests passed: {passed}/{total}")
        
        if passed == total:
            print("🎉 All tests passed! EmailImportWorker should work correctly.")
        else:
            print("⚠️ Some issues found. Check the failed tests above.")
            print("\n💡 Common solutions:")
            print("   • Ensure credentials.json and token.json exist")
            print("   • Check Gmail API quotas and permissions")
            print("   • Verify active integrations in database")
            print("   • Remove AFP_Processed labels to find new emails")
        
        return passed == total

def main():
    """Main execution"""
    tester = EmailImportTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 