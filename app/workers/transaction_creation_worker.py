import re
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any

from .base_worker import BaseWorker
from ..models.email_parsing_job import EmailParsingJob
from ..models.job_queue import JobQueue
from ..models.bank import Bank

from ..models.transaction import Transaction
from ..models.bank_email_template import BankEmailTemplate

from ..services.bank_template_service import BankTemplateService
from ..core.database import db


class TransactionCreationWorker(BaseWorker):
    """
    Worker that processes EmailParsingJobs to extract transactions.
    
    Continuously processes JobQueue entries for 'email_parsing':
    1. Takes job from queue
    2. Identifies bank from email
    3. Applies parsing rules to extract transaction data
    4. Creates Transaction if successful
    """
    
    def __init__(self):
        super().__init__(name="TransactionCreation", sleep_interval=1.0)
        self.ai_rule_generator = None  # Initialize lazily to handle missing API key gracefully
        self.template_service = BankTemplateService()  # New template-based processing
    
    def process_cycle(self):
        """Process one email parsing job from the queue"""
        try:
            # Get next job from queue
            queue_job = db.session.query(JobQueue).filter_by(
                queue_name='email_parsing',
                status='pending'
            ).order_by(JobQueue.priority.desc(), JobQueue.created_at.asc()).first()
            
            if not queue_job:
                return  # No jobs to process
            
            # Get associated EmailParsingJob
            parsing_job_id = queue_job.job_data.get('email_parsing_job_id')
            if not parsing_job_id:
                self.logger.error(f"Invalid job data in queue job {queue_job.id}")
                queue_job.status = 'failed'
                queue_job.error_message = 'Invalid job data'
                db.session.commit()
                return
            
            parsing_job = db.session.query(EmailParsingJob).get(parsing_job_id)
            if not parsing_job:
                self.logger.error(f"EmailParsingJob {parsing_job_id} not found")
                queue_job.status = 'failed'
                queue_job.error_message = 'EmailParsingJob not found'
                db.session.commit()
                return
            
            # Mark jobs as running
            queue_job.status = 'running'
            queue_job.worker_id = self.worker_id
            queue_job.started_at = datetime.now(UTC)
            
            parsing_job.status = 'running'
            parsing_job.worker_id = self.worker_id
            parsing_job.started_at = datetime.now(UTC)
            
            db.session.commit()
            
            self.logger.info(f"Processing EmailParsingJob {parsing_job.id}")
            
            # Process the job
            try:
                result = self._process_email_parsing(parsing_job)
                
                # Update parsing job status based on result
                if result['success']:
                    parsing_job.status = 'completed'
                    parsing_job.summary = 'transaction_created'
                    parsing_job.extracted_data = result['transaction_data']
                    parsing_job.parsing_rules_used = result['rules_used']
                    parsing_job.confidence_score = result['confidence_score']
                    
                    queue_job.status = 'completed'
                    
                    self.logger.info(
                        f"Successfully extracted transaction from EmailParsingJob {parsing_job.id} "
                        f"(confidence: {result['confidence_score']:.2f})"
                    )
                else:
                    parsing_job.status = 'completed'  # Job completed, but no transaction
                    parsing_job.summary = result['status']  # no_bank_identified, no_transaction_found, etc.
                    parsing_job.error_message = result.get('error_message')
                    
                    queue_job.status = 'completed'  # Job completed, even if no transaction found
                    
                    self.logger.info(f"No transaction extracted from EmailParsingJob {parsing_job.id}: {result['status']}")
                
                parsing_job.completed_at = datetime.now(UTC)
                queue_job.completed_at = datetime.now(UTC)
                
            except Exception as e:
                # Handle job failure
                parsing_job.status = 'error'
                parsing_job.summary = 'processing_error'
                parsing_job.error_message = str(e)
                parsing_job.completed_at = datetime.now(UTC)
                
                queue_job.status = 'failed'
                queue_job.error_message = str(e)
                queue_job.completed_at = datetime.now(UTC)
                
                self.logger.error(f"Failed to process EmailParsingJob {parsing_job.id}: {str(e)}")
            
            finally:
                parsing_job.worker_id = None
                queue_job.worker_id = None
                db.session.commit()
                
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error in transaction creation cycle: {str(e)}")
            raise
    
    def _process_email_parsing(self, parsing_job: EmailParsingJob) -> Dict[str, Any]:
        """Process a single email parsing job"""
        try:
            # Identify bank from email - check if already assigned or identify now
            if parsing_job.bank_id:
                # Bank already assigned, get it from database
                bank = db.session.query(Bank).get(parsing_job.bank_id)
                if not bank:
                    self.logger.warning(f"EmailParsingJob {parsing_job.id} has invalid bank_id: {parsing_job.bank_id}")
                    bank = self._identify_bank(parsing_job.email_from, parsing_job.email_subject)
            else:
                # Bank not assigned, identify from email content
                bank = self._identify_bank(parsing_job.email_from, parsing_job.email_subject)
                if bank:
                    # Assign bank to the parsing job for future reference
                    parsing_job.bank_id = bank.id
                    self.logger.info(f"Identified and assigned bank {bank.name} to EmailParsingJob {parsing_job.id}")
            
            if not bank:
                return {
                    'success': False,
                    'status': 'no_bank_identified',
                    'error_message': f'Could not identify bank from sender: {parsing_job.email_from}'
                }
            
            # NEW TEMPLATE-BASED PROCESSING: Try to find best matching template
            best_template_id = self.template_service.find_best_template(
                bank.id,
                parsing_job.email_subject or '',
                parsing_job.email_from or '',
                parsing_job.email_body or ''
            )
            
            if best_template_id:
                # Load template in current session
                template = db.session.query(BankEmailTemplate).get(best_template_id)
                if not template:
                    self.logger.error(f"Failed to load template {best_template_id}")
                else:
                    # Extract data using template
                    self.logger.info(f"Using template '{template.template_name}' for bank {bank.name}")
                    extraction_result = self.template_service.extract_transaction_data(
                        template, 
                        parsing_job.email_body or ''
                    )
                    
                    if extraction_result['confidence_score'] > 0.3:  # Lowered threshold from 0.5
                        # Template extraction successful
                        transaction_data = self._clean_template_extraction(extraction_result['extracted_data'])
                        if transaction_data:
                            # Create transaction
                            transaction = self._create_transaction(parsing_job, bank, transaction_data)
                            
                            return {
                                'success': True,
                                'transaction_data': transaction_data,
                                'rules_used': [f"template:{template.id}:{template.template_name}"],
                                'confidence_score': extraction_result['confidence_score'],
                                'transaction_id': transaction.id
                            }
                        else:
                            self.logger.warning(f"Template extraction had confidence {extraction_result['confidence_score']:.2f} but data cleaning failed")
                    else:
                        self.logger.info(f"Template extraction confidence too low: {extraction_result['confidence_score']:.2f}")
            
            # FALLBACK: Check if we have templates for this bank, if not generate one
            existing_templates = self.template_service.get_templates_for_bank(bank.id)
            if not existing_templates:
                # NO LONGER AUTO-GENERATE: Return error instead
                return {
                    'success': False,
                    'status': 'no_templates_configured',
                    'error_message': f'No email templates configured for bank: {bank.name}. Please configure templates in setup.'
                }
            
            # No templates configured - return clear error
            return {
                'success': False,
                'status': 'no_templates_configured',
                'error_message': f'No email templates configured for bank: {bank.name}. Please run bank setup to configure templates.'
            }
            
        except Exception as e:
            self.logger.error(f"Error processing email parsing: {str(e)}")
            raise
    
    def _identify_bank(self, sender: str, subject: str) -> Optional[Bank]:
        """Identify bank from email sender and subject"""
        # Get all banks and check their email patterns
        banks = db.session.query(Bank).filter_by(is_active=True).all()
        
        for bank in banks:
            # Check if sender matches bank's sender emails or domains
            if bank.sender_emails:
                for email in bank.sender_emails:
                    if email.lower() in sender.lower():
                        return bank
            
            if bank.sender_domains:
                for domain in bank.sender_domains:
                    if domain.lower() in sender.lower():
                        return bank
            
            # Also check subject for bank name
            if bank.name.lower() in subject.lower():
                return bank
        
        return None
    

    
    def _clean_template_extraction(self, raw_data: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Clean and validate template extraction data"""
        try:
            cleaned = {}
            
            # Clean amount - REQUIRED
            if 'amount' in raw_data and raw_data['amount']:
                amount_str = raw_data['amount']
                # Remove currency symbols and formatting
                amount_str = re.sub(r'[^\d,.-]', '', amount_str)  # Keep only numbers, commas, dots, minus
                amount_str = amount_str.replace(',', '')  # Remove thousands separators
                
                # Handle negative amounts (withdrawals)
                if amount_str.startswith('-'):
                    amount_str = amount_str[1:]
                    cleaned['is_debit'] = True
                else:
                    cleaned['is_debit'] = False
                    
                try:
                    cleaned['amount'] = float(amount_str)
                except ValueError:
                    self.logger.warning(f"Failed to parse amount: {raw_data['amount']}")
                    return None
            else:
                return None  # Amount is required
            
            # Clean description
            if 'description' in raw_data and raw_data['description']:
                cleaned['description'] = raw_data['description'].strip()[:500]
            
            # Clean merchant (can be mapped to source)
            if 'merchant' in raw_data and raw_data['merchant']:
                cleaned['source'] = raw_data['merchant'].strip()[:255]
            
            # Clean date
            if 'date' in raw_data and raw_data['date']:
                date_str = raw_data['date'].strip()
                # Try multiple date formats common in banking emails
                date_formats = [
                    '%d/%m/%Y',    # DD/MM/YYYY
                    '%m/%d/%Y',    # MM/DD/YYYY
                    '%Y-%m-%d',    # YYYY-MM-DD
                    '%d-%m-%Y',    # DD-MM-YYYY
                    '%d/%m/%Y %H:%M:%S',  # DD/MM/YYYY HH:MM:SS
                    '%Y-%m-%d %H:%M:%S'   # YYYY-MM-DD HH:MM:SS
                ]
                
                parsed_date = None
                for fmt in date_formats:
                    try:
                        parsed_date = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
                
                cleaned['date'] = parsed_date if parsed_date else datetime.now(UTC)
            else:
                cleaned['date'] = datetime.now(UTC)  # Default to now if no date found
            
            # Clean reference (can be used for tracking)
            if 'reference' in raw_data and raw_data['reference']:
                cleaned['reference'] = raw_data['reference'].strip()[:100]
            
            return cleaned
            
        except Exception as e:
            self.logger.error(f"Error cleaning template extraction data: {str(e)}")
            return None
    
    def _create_transaction(self, parsing_job: EmailParsingJob, bank: Bank, transaction_data: Dict[str, Any]) -> Transaction:
        """Create a new Transaction from extracted data"""
        transaction = Transaction(
            description=transaction_data.get('description', ''),
            amount=transaction_data['amount'],
            date=transaction_data.get('date', datetime.now(UTC)),
            source=transaction_data.get('source', 'email_parsing'),
            email_id=parsing_job.email_message_id,  # Use email message ID for tracking
            from_bank=transaction_data.get('from_bank', bank.name),  # Default to identified bank
            to_bank=transaction_data.get('to_bank'),
            email_parsing_job_id=parsing_job.id,  # Link to parsing job
            confidence_score=transaction_data.get('confidence_score', 0.5),  # Default confidence
            verification_status='auto',  # Mark as automatically created
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        
        return transaction
    
    def reset_worker_jobs(self):
        """Reset jobs that were being processed by this worker"""
        try:
            # Reset EmailParsingJobs
            stuck_parsing_jobs = db.session.query(EmailParsingJob).filter_by(
                worker_id=self.worker_id,
                status='running'
            ).all()
            
            for job in stuck_parsing_jobs:
                job.status = 'error'
                job.summary = 'worker_stopped'
                job.error_message = 'Worker stopped unexpectedly'
                job.worker_id = None
                self.logger.info(f"Reset stuck EmailParsingJob {job.id}")
            
            # Reset JobQueue entries
            stuck_queue_jobs = db.session.query(JobQueue).filter_by(
                worker_id=self.worker_id,
                status='running',
                queue_name='email_parsing'
            ).all()
            
            for job in stuck_queue_jobs:
                job.status = 'failed'
                job.error_message = 'Worker stopped unexpectedly'
                job.worker_id = None
                self.logger.info(f"Reset stuck JobQueue entry {job.id}")
                
        except Exception as e:
            self.logger.error(f"Error resetting worker jobs: {str(e)}") 