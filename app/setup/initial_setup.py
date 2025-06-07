"""
Initial setup for AFP - Create user and Gmail integration automatically
"""

import logging
import json
import os
from datetime import datetime, timedelta, UTC
from app.core.database import DatabaseSession
from app.models.user import User
from app.models.integration import Integration
from app.models.email_import_job import EmailImportJob
from app.models.bank import Bank

from app.models.bank_email_template import BankEmailTemplate
from ..services.bank_setup_service import BankSetupService

logger = logging.getLogger(__name__)

def _load_tokens_from_file(token_path="token.json"):
    """Load access and refresh tokens from token.json file"""
    try:
        if not os.path.exists(token_path):
            logger.info(f"📄 No token file found at {token_path}")
            return None, None
        
        with open(token_path, 'r') as f:
            token_data = json.load(f)
        
        access_token = token_data.get('token')
        refresh_token = token_data.get('refresh_token')
        
        if access_token and refresh_token:
            logger.info(f"✅ Loaded tokens from {token_path}")
            return access_token, refresh_token
        else:
            logger.warning(f"⚠️ Token file incomplete: missing access_token or refresh_token")
            return None, None
            
    except Exception as e:
        logger.error(f"❌ Error loading tokens from {token_path}: {str(e)}")
        return None, None

def _update_integration_tokens(integration, db):
    """Update integration with tokens from token.json if available"""
    try:
        access_token, refresh_token = _load_tokens_from_file()
        
        if access_token and refresh_token:
            # Only update if tokens are different or missing
            if integration.access_token != access_token or integration.refresh_token != refresh_token:
                integration.access_token = access_token
                integration.refresh_token = refresh_token
                integration.updated_at = datetime.now(UTC)
                db.commit()
                logger.info(f"✅ Updated integration {integration.id} with current tokens")
            else:
                logger.info(f"✅ Integration {integration.id} already has current tokens")
        else:
            logger.info(f"📄 No valid tokens found to update integration {integration.id}")
            
    except Exception as e:
        logger.error(f"❌ Error updating integration tokens: {str(e)}")

def create_default_user():
    """Create default user with luisggm33@gmail.com"""
    
    with DatabaseSession() as db:
        return _create_default_user_in_session(db)

def _create_default_user_in_session(db):
    """Create default user with luisggm33@gmail.com within existing session"""
    # Check if user already exists
    existing_user = db.query(User).filter_by(email="luisggm33@gmail.com").first()
    if existing_user:
        logger.info(f"✅ User already exists: {existing_user.email}")
        return existing_user
    
    # Create new user
    user = User(
        email="luisggm33@gmail.com",
        full_name="Luis Gabriel",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )
    
    db.add(user)
    db.flush()  # Get ID without committing
    
    logger.info(f"✅ Created default user: {user.email} (ID: {user.id})")
    return user

def create_gmail_integration(user):
    """Create Gmail integration for the user"""
    
    with DatabaseSession() as db:
        return _create_gmail_integration_in_session(db, user)

def _create_gmail_integration_in_session(db, user):
    """Create Gmail integration for the user within existing session"""
    # Check if integration already exists
    existing_integration = db.query(Integration).filter_by(
        user_id=user.id,
        provider="gmail"
    ).first()
    
    if existing_integration:
        logger.info(f"✅ Gmail integration already exists for user {user.email}")
        # Update tokens if we have newer ones from token.json
        _update_integration_tokens(existing_integration, db)
        return existing_integration
    
    # Try to load existing tokens from token.json
    access_token, refresh_token = _load_tokens_from_file()
    
    # Create new Gmail integration
    integration = Integration(
        user_id=user.id,
        provider="gmail",
        email_account="luisggm33@gmail.com",
        is_active=True,
        sync_frequency_minutes=15,  # Check every 15 minutes
        access_token=access_token,
        refresh_token=refresh_token,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )
    
    db.add(integration)
    db.flush()  # Get ID without committing
    
    if access_token:
        logger.info(f"✅ Created Gmail integration with existing tokens: {integration.email_account} (ID: {integration.id})")
    else:
        logger.info(f"✅ Created Gmail integration (tokens pending): {integration.email_account} (ID: {integration.id})")
    
    return integration

def create_email_import_job(integration):
    """Create EmailImportJob for the integration"""
    
    with DatabaseSession() as db:
        return _create_email_import_job_in_session(db, integration)

def _create_email_import_job_in_session(db, integration):
    """Create EmailImportJob for the integration within existing session"""
    # Check if EmailImportJob already exists
    existing_job = db.query(EmailImportJob).filter_by(
        integration_id=integration.id
    ).first()
    
    if existing_job:
        logger.info(f"✅ EmailImportJob already exists for integration {integration.id}")
        return existing_job
    
    # Create new EmailImportJob
    now = datetime.now(UTC)
    email_import_job = EmailImportJob(
        integration_id=integration.id,
        status="idle",  # Ready to be picked up by workers
        last_run_at=None,  # Never run before
        next_run_at=now,  # Available immediately
        total_runs=0,
        consecutive_errors=0,
        run_history=[],  # Empty history
        created_at=now,
        updated_at=now
    )
    
    db.add(email_import_job)
    db.flush()  # Get ID without committing
    
    logger.info(f"✅ Created EmailImportJob: ID {email_import_job.id} for integration {integration.id}")
    return email_import_job

def setup_oauth_instructions(integration):
    """Show OAuth setup status and instructions if needed"""
    if integration.access_token and integration.refresh_token:
        logger.info("✅ GMAIL OAUTH ALREADY CONFIGURED:")
        logger.info("="*60)
        logger.info("Gmail API tokens are loaded and ready to use!")
        logger.info("")
        logger.info(f"Integration ID: {integration.id}")
        logger.info(f"Email account: {integration.email_account}")
        logger.info(f"Tokens loaded from: token.json")
        logger.info("")
        logger.info("🚀 The system is ready to process emails automatically!")
        logger.info("="*60)
    else:
        logger.info("📋 GMAIL OAUTH SETUP REQUIRED:")
        logger.info("="*60)
        logger.info("To enable automatic email import, you need to complete OAuth setup:")
        logger.info("")
        logger.info("1. Go to Google Cloud Console: https://console.cloud.google.com/")
        logger.info("2. Create credentials for Gmail API (OAuth 2.0)")
        logger.info("3. Download credentials.json")
        logger.info("4. Place it in: app/infrastructure/email/credentials.json")
        logger.info("5. Run OAuth authorization script")
        logger.info("")
        logger.info(f"Integration ID created: {integration.id}")
        logger.info(f"Email account: {integration.email_account}")
        logger.info("="*60)

def create_default_banks():
    """Create default banks and their parsing rules"""
    logger.info("🏦 Creating default banks and parsing rules...")
    
    with DatabaseSession() as db:
        # Banks configuration
        banks_config = [
        {
            'name': 'BAC Costa Rica',
            'bank_code': 'BAC',
            'domain': 'notificacionesbaccr.com',
            'sender_emails': ['notificacion@notificacionesbaccr.com'],
            'sender_domains': ['notificacionesbaccr.com', 'baccredomatic.com'],

        },
        {
            'name': 'Scotiabank Costa Rica',
            'bank_code': 'SCOTIA',
            'domain': 'scotiabank.com',
            'sender_emails': ['AlertasScotiabank@scotiabank.com'],
            'sender_domains': ['scotiabank.com'],

        },
        {
            'name': 'Banco de Costa Rica',
            'bank_code': 'BCR',
            'domain': 'bancobcr.com',
            'sender_emails': ['mensajero@bancobcr.com'],
            'sender_domains': ['bancobcr.com'],

                }
        ]
        
        banks_created = 0
        rules_created = 0
        
        for bank_config in banks_config:
            # Check if bank already exists
            existing_bank = db.query(Bank).filter_by(bank_code=bank_config['bank_code']).first()
            
            if existing_bank:
                logger.info(f"✅ Bank already exists: {existing_bank.name}")
                bank = existing_bank
            else:
                # Create new bank
                bank = Bank(
                    name=bank_config['name'],
                    bank_code=bank_config['bank_code'],
                    domain=bank_config['domain'],
                    sender_emails=bank_config.get('sender_emails', []),
                    sender_domains=bank_config.get('sender_domains', []),
                    country_code="CR",  # Costa Rica
                    bank_type="commercial",
                    is_active=True,
                    parsing_priority=10,
                    website=f"https://www.{bank_config['bank_code'].lower()}.co.cr",
                    confidence_threshold=0.8,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC)
                )
                
                db.add(bank)
                db.flush()  # To get the ID
                banks_created += 1
                logger.info(f"✅ Created bank: {bank.name} (ID: {bank.id})")
            
            # Note: Parsing rules are obsolete, now using BankEmailTemplates via BankSetupService
        
        db.commit()
        
        logger.info(f"🎯 Banks setup complete: {banks_created} banks created")
        return banks_created, 0  # rules_created is now 0 since we don't create parsing rules

def _create_default_banks_in_session(db):
    """Create default banks and their parsing rules within existing session"""
    logger.info("🏦 Creating default banks and parsing rules...")
    
    # Banks configuration (templates are now created via BankSetupService)
    banks_config = [
        {
            'name': 'BAC Costa Rica',
            'bank_code': 'BAC',
            'domain': 'notificacionesbaccr.com',
            'sender_emails': ['notificacion@notificacionesbaccr.com'],
            'sender_domains': ['notificacionesbaccr.com', 'baccredomatic.com']
        },
        {
            'name': 'Scotiabank Costa Rica',
            'bank_code': 'SCOTIA',
            'domain': 'scotiabank.com',
            'sender_emails': ['AlertasScotiabank@scotiabank.com'],
            'sender_domains': ['scotiabank.com']
        },
        {
            'name': 'Banco de Costa Rica',
            'bank_code': 'BCR',
            'domain': 'bancobcr.com',
            'sender_emails': ['mensajero@bancobcr.com'],
            'sender_domains': ['bancobcr.com']
        }
    ]
    
    banks_created = 0
    
    for bank_config in banks_config:
        # Check if bank already exists
        existing_bank = db.query(Bank).filter_by(bank_code=bank_config['bank_code']).first()
        
        if existing_bank:
            logger.info(f"✅ Bank already exists: {existing_bank.name}")
            bank = existing_bank
        else:
            # Create new bank
            bank = Bank(
                name=bank_config['name'],
                bank_code=bank_config['bank_code'],
                domain=bank_config['domain'],
                sender_emails=bank_config.get('sender_emails', []),
                sender_domains=bank_config.get('sender_domains', []),
                country_code="CR",  # Costa Rica
                bank_type="commercial",
                is_active=True,
                parsing_priority=10,
                website=f"https://www.{bank_config['bank_code'].lower()}.co.cr",
                confidence_threshold=0.8,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            
            db.add(bank)
            db.flush()  # To get the ID
            banks_created += 1
            logger.info(f"✅ Created bank: {bank.name} (ID: {bank.id})")
        
        # Note: Parsing rules are obsolete, now using BankEmailTemplates via BankSetupService
    
    logger.info(f"🎯 Banks setup complete: {banks_created} banks created")
    return banks_created, 0  # rules_created is now 0 since we don't create parsing rules

def run_initial_setup():
    """Run the complete initial setup"""
    try:
        logger.info("🎬 RUNNING INITIAL AFP SETUP")
        logger.info("="*50)
        
        with DatabaseSession() as db:
            # Create default user
            user = _create_default_user_in_session(db)
            
            # Create Gmail integration
            integration = _create_gmail_integration_in_session(db, user)
            
            # Create EmailImportJob
            email_import_job = _create_email_import_job_in_session(db, integration)
            
            # Create default banks and parsing rules (legacy)
            banks_created, rules_created = _create_default_banks_in_session(db)
            
            # Commit all basic setup changes at once
            db.commit()
        
        # NEW: Setup banks with templates (after basic setup is committed)
        logger.info("\n🏦 SETTING UP BANK TEMPLATES...")
        bank_setup_results = setup_banks_with_templates()
        
        # Show OAuth setup instructions
        setup_oauth_instructions(integration)
        
        logger.info("🎉 INITIAL SETUP COMPLETED SUCCESSFULLY!")
        logger.info(f"   User: {user.email} (ID: {user.id})")
        logger.info(f"   Integration: {integration.email_account} (ID: {integration.id})")
        logger.info(f"   EmailImportJob: ID {email_import_job.id}")
        logger.info(f"   Banks created: {banks_created}, Parsing rules: {rules_created}")
        
        # Show template setup results
        if bank_setup_results:
            successful_banks = len([r for r in bank_setup_results if r['success']])
            total_templates = sum(r.get('templates_created', 0) for r in bank_setup_results if r['success'])
            logger.info(f"   Bank templates: {successful_banks} banks configured, {total_templates} templates created")
        
        logger.info("")
        
        if integration.access_token and integration.refresh_token:
            logger.info("🚀 AFP is ready to start processing emails immediately!")
        else:
            logger.info("🚀 AFP is ready to start processing emails once OAuth is completed!")
        
        return {
            'user': user,
            'integration': integration,
            'email_import_job': email_import_job,
            'bank_setup_results': bank_setup_results
        }
        
    except Exception as e:
        logger.error(f"❌ Error in initial setup: {str(e)}")
        raise

def check_setup_status():
    """Check if initial setup has been completed"""
    try:
        with DatabaseSession() as db:
            user = db.query(User).filter_by(email="luisggm33@gmail.com").first()
            if not user:
                return False, "User not found"
            
            integration = db.query(Integration).filter_by(
                user_id=user.id,
                provider="gmail"
            ).first()
            
            if not integration:
                return False, "Gmail integration not found"
            
            email_import_job = db.query(EmailImportJob).filter_by(
                integration_id=integration.id
            ).first()
            
            if not email_import_job:
                return False, "EmailImportJob not found"
            
            # Check if OAuth is completed
            oauth_completed = integration.access_token is not None
            
            return True, {
                'user_id': user.id,
                'integration_id': integration.id,
                'email_import_job_id': email_import_job.id,
                'oauth_completed': oauth_completed
            }
        
    except Exception as e:
        return False, f"Error checking setup: {str(e)}"

def setup_banks_with_templates():
    """Setup banks and generate templates using the new BankSetupService"""
    logger.info("🏦 SETTING UP BANKS WITH TEMPLATES")
    logger.info("="*50)
    
    bank_setup_service = BankSetupService()
    
    try:
        # Setup default Costa Rican banks
        results = bank_setup_service.setup_default_costa_rican_banks()
        
        total_banks = len(results)
        successful_banks = len([r for r in results if r['success']])
        total_templates = sum(r.get('templates_created', 0) for r in results if r['success'])
        
        logger.info(f"✅ Bank setup completed:")
        logger.info(f"   Banks processed: {total_banks}")
        logger.info(f"   Banks successful: {successful_banks}")
        logger.info(f"   Templates created: {total_templates}")
        
        for result in results:
            if result['success']:
                logger.info(f"   ✅ {result['bank_name']}: {result['message']}")
            else:
                logger.error(f"   ❌ {result['bank_name']}: {result.get('error', 'Unknown error')}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error in bank setup: {str(e)}")
        raise 