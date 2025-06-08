#!/usr/bin/env python3
"""
Bank Setup Service - Handles bank configuration and template generation during initial setup.
This service is responsible for:
1. Configuring banks with their email patterns
2. Generating email templates for each bank
3. Validating bank configurations
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, UTC
import logging

from ..core.database import DatabaseSession
from ..models.bank import Bank
from ..models.email_parsing_job import EmailParsingJob
from ..models.bank_email_template import BankEmailTemplate
from .bank_template_service import BankTemplateService

logger = logging.getLogger(__name__)

class BankSetupService:
    """Service for configuring banks and generating templates during setup"""
    
    def __init__(self):
        self.template_service = BankTemplateService()
    
    def configure_bank_with_templates(self, bank_name: str, sender_emails: List[str], sender_domains: List[str], bank_code: str = None) -> Dict:
        """
        Configure a bank and generate templates if needed.
        
        Args:
            bank_name: Name of the bank
            sender_emails: List of email addresses the bank sends from
            sender_domains: List of domains the bank sends from
            bank_code: Optional bank code, will be generated if not provided
            
        Returns:
            Dict with configuration results
        """
        logger.info(f"Configuring bank: {bank_name}")
        
        with DatabaseSession() as db:
            # Find existing bank by name or bank_code
            bank = db.query(Bank).filter(
                (Bank.name == bank_name) | 
                (Bank.bank_code == bank_code if bank_code else False)
            ).first()
            
            if not bank:
                # Generate bank_code and domain from name if not provided
                if not bank_code:
                    bank_code = bank_name.upper().replace(' ', '_')[:10]
                domain = sender_domains[0] if sender_domains else f"{bank_name.lower().replace(' ', '')}.com"
                
                bank = Bank(
                    name=bank_name,
                    bank_code=bank_code,
                    domain=domain,
                    sender_emails=sender_emails,
                    sender_domains=sender_domains,
                    is_active=True,
                    country_code="CR",
                    bank_type="commercial",
                    parsing_priority=10,
                    confidence_threshold=0.7,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC)
                )
                db.add(bank)
                db.commit()
                db.refresh(bank)
                logger.info(f"Created new bank: {bank_name} (ID: {bank.id})")
            else:
                # Update sender information
                bank.sender_emails = sender_emails
                bank.sender_domains = sender_domains
                bank.updated_at = datetime.now(UTC)
                db.commit()
                logger.info(f"Updated existing bank: {bank_name} (ID: {bank.id})")
            
            # Check for existing templates
            existing_templates = db.query(BankEmailTemplate).filter_by(
                bank_id=bank.id,
                is_active=True
            ).count()
            
            if existing_templates > 0:
                logger.info(f"Bank {bank_name} already has {existing_templates} templates")
                return {
                    'success': True,
                    'bank_id': bank.id,
                    'bank_name': bank_name,
                    'templates_created': 0,
                    'templates_existing': existing_templates,
                    'message': f'Bank configured. Using {existing_templates} existing templates.'
                }
            
            # Generate templates using sample emails
            templates_created = self._generate_templates_for_bank(bank)
            
            return {
                'success': True,
                'bank_id': bank.id,
                'bank_name': bank_name,
                'templates_created': templates_created,
                'templates_existing': 0,
                'message': f'Bank configured with {templates_created} new templates.'
            }
    
    def _generate_templates_for_bank(self, bank: Bank) -> int:
        """
        Generate templates for a bank using existing sample emails.
        
        Args:
            bank: Bank object
            
        Returns:
            Number of templates created
        """
        logger.info(f"Generating templates for {bank.name}")
        
        with DatabaseSession() as db:
            # Get sample emails from this bank
            sample_emails = db.query(EmailParsingJob).filter_by(
                bank_id=bank.id
            ).order_by(EmailParsingJob.created_at.desc()).limit(10).all()
            
            if not sample_emails:
                logger.warning(f"No sample emails found for {bank.name}, cannot generate templates")
                return 0
            
            logger.info(f"Found {len(sample_emails)} sample emails for {bank.name}")
            
            # Group emails by type (we could analyze subjects/content to detect different types)
            email_groups = self._group_emails_by_type(sample_emails)
            
            templates_created = 0
            
            for email_type, emails in email_groups.items():
                try:
                    # Generate template for this email type
                    template_id = self.template_service.auto_generate_template(
                        bank.id,
                        emails,
                        template_type=email_type
                    )
                    
                    if template_id:
                        templates_created += 1
                        logger.info(f"Created template ID {template_id} for {bank.name}")
                    else:
                        logger.warning(f"Failed to create template for {email_type} emails in {bank.name}")
                        
                except Exception as e:
                    logger.error(f"Error creating template for {email_type} in {bank.name}: {e}")
                    continue
            
            return templates_created
    
    def _group_emails_by_type(self, emails: List[EmailParsingJob]) -> Dict[str, List[EmailParsingJob]]:
        """
        Group emails by type based on subject patterns.
        For now, we'll use a simple approach - in the future this could be more sophisticated.
        
        Args:
            emails: List of email parsing jobs
            
        Returns:
            Dict mapping email type to list of emails
        """
        groups = {
            'transaction': [],  # Default group for transaction emails
        }
        
        # For now, put all emails in the transaction group
        # In the future, we could analyze subjects to detect different types:
        # - purchase vs withdrawal
        # - ATM vs merchant
        # - etc.
        
        for email in emails:
            # Simple classification based on subject keywords
            subject = (email.email_subject or '').lower()
            
            if any(keyword in subject for keyword in ['compra', 'purchase', 'transacción', 'transaction']):
                groups['transaction'].append(email)
            elif any(keyword in subject for keyword in ['retiro', 'withdrawal', 'atm']):
                if 'withdrawal' not in groups:
                    groups['withdrawal'] = []
                groups['withdrawal'].append(email)
            elif any(keyword in subject for keyword in ['transferencia', 'transfer']):
                if 'transfer' not in groups:
                    groups['transfer'] = []
                groups['transfer'].append(email)
            else:
                # Default to transaction group
                groups['transaction'].append(email)
        
        # Remove empty groups
        groups = {k: v for k, v in groups.items() if v}
        
        logger.info(f"Grouped emails: {[(k, len(v)) for k, v in groups.items()]}")
        return groups
    
    def validate_bank_configuration(self, bank_id: int) -> Dict:
        """
        Validate that a bank is properly configured with templates.
        
        Args:
            bank_id: ID of the bank to validate
            
        Returns:
            Dict with validation results
        """
        with DatabaseSession() as db:
            bank = db.query(Bank).get(bank_id)
            if not bank:
                return {
                    'valid': False,
                    'error': f'Bank with ID {bank_id} not found'
                }
            
            # Check templates
            templates = db.query(BankEmailTemplate).filter_by(
                bank_id=bank_id,
                is_active=True
            ).all()
            
            if not templates:
                return {
                    'valid': False,
                    'bank_name': bank.name,
                    'error': f'No active templates found for {bank.name}'
                }
            
            # Check sender configuration
            if not bank.sender_emails and not bank.sender_domains:
                return {
                    'valid': False,
                    'bank_name': bank.name,
                    'error': f'No sender emails or domains configured for {bank.name}'
                }
            
            return {
                'valid': True,
                'bank_name': bank.name,
                'templates_count': len(templates),
                'sender_emails': len(bank.sender_emails or []),
                'sender_domains': len(bank.sender_domains or [])
            }
    
    def get_banks_needing_setup(self) -> List[Dict]:
        """
        Get list of banks that need template setup.
        
        Returns:
            List of banks that need configuration
        """
        with DatabaseSession() as db:
            banks = db.query(Bank).filter_by(is_active=True).all()
            needs_setup = []
            
            for bank in banks:
                templates_count = db.query(BankEmailTemplate).filter_by(
                    bank_id=bank.id,
                    is_active=True
                ).count()
                
                if templates_count == 0:
                    needs_setup.append({
                        'bank_id': bank.id,
                        'bank_name': bank.name,
                        'sender_emails': len(bank.sender_emails or []),
                        'sender_domains': len(bank.sender_domains or [])
                    })
            
            return needs_setup
    
    def setup_default_costa_rican_banks(self) -> List[Dict]:
        """
        Setup default Costa Rican banks with their known sender patterns.
        
        Returns:
            List of setup results for each bank
        """
        costa_rican_banks = [
            {
                'name': 'BAC Costa Rica',
                'bank_code': 'BAC_CR',
                'sender_emails': ['notificacion@notificacionesbaccr.com'],
                'sender_domains': ['notificacionesbaccr.com', 'baccredomatic.com']
            },
            {
                'name': 'Scotiabank Costa Rica',
                'bank_code': 'SCOTIA_CR',
                'sender_emails': ['AlertasScotiabank@scotiabank.com'],
                'sender_domains': ['scotiabank.com']
            },
            {
                'name': 'Banco Nacional Costa Rica',
                'bank_code': 'BNCR',
                'sender_emails': ['notificaciones@bncr.fi.cr', 'tarjetas@bncr.fi.cr'],
                'sender_domains': ['bncr.fi.cr']
            },
            {
                'name': 'Banco Popular Costa Rica',
                'bank_code': 'POPULAR_CR',
                'sender_emails': ['notificaciones@bancopopular.fi.cr'],
                'sender_domains': ['bancopopular.fi.cr']
            }
        ]
        
        results = []
        for bank_config in costa_rican_banks:
            try:
                result = self.configure_bank_with_templates(
                    bank_config['name'],
                    bank_config['sender_emails'],
                    bank_config['sender_domains'],
                    bank_config['bank_code']
                )
                results.append(result)
                logger.info(f"Setup completed for {bank_config['name']}: {result['message']}")
            except Exception as e:
                logger.error(f"Error setting up {bank_config['name']}: {e}")
                results.append({
                    'success': False,
                    'bank_name': bank_config['name'],
                    'error': str(e)
                })
        
        return results 