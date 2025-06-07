import re
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.bank_email_template import BankEmailTemplate
from app.models.bank import Bank
from app.models.email_parsing_job import EmailParsingJob
from app.core.database import DatabaseSession
from app.services.ai_rule_generator import AIRuleGeneratorService

logger = logging.getLogger(__name__)

class BankTemplateService:
    """
    Service for managing bank email templates with AI-powered auto-generation.
    Supports multiple templates per bank for different transaction types.
    """
    
    def __init__(self):
        self.ai_service = None  # Initialize lazily when needed
    
    def _get_ai_service(self):
        """Initialize AI service lazily to handle missing API keys gracefully"""
        if self.ai_service is None:
            try:
                self.ai_service = AIRuleGeneratorService()
            except ValueError as e:
                logger.warning(f"AI service not available: {e}")
                return None
        return self.ai_service
    
    def find_best_template(self, bank_id: int, email_subject: str, email_sender: str, email_body: str) -> Optional[int]:
        """
        Find the best matching template for an email from a specific bank.
        Returns the template ID (not the object) to avoid session issues.
        """
        with DatabaseSession() as db:
            # Get all active templates for this bank, ordered by priority
            templates = db.query(BankEmailTemplate).filter(
                BankEmailTemplate.bank_id == bank_id,
                BankEmailTemplate.is_active == True
            ).order_by(desc(BankEmailTemplate.priority)).all()
            
            if not templates:
                logger.info(f"No templates found for bank_id={bank_id}")
                return None
            
            best_template = None
            best_score = 0.0
            
            for template in templates:
                match_score = template.calculate_match_score(email_subject, email_sender, email_body)
                logger.debug(f"Template '{template.template_name}' scored {match_score:.2f}")
                
                if match_score >= template.confidence_threshold and match_score > best_score:
                    best_template = template
                    best_score = match_score
            
            if best_template:
                logger.info(f"Selected template '{best_template.template_name}' with score {best_score:.2f}")
                # Update last used timestamp - reload to avoid detached instance
                fresh_template = db.query(BankEmailTemplate).get(best_template.id)
                if fresh_template:
                    fresh_template.last_used_at = datetime.utcnow()
                    db.commit()
                
                # Return only the ID to avoid session issues
                return best_template.id
            else:
                logger.info(f"No template met confidence threshold for bank_id={bank_id}")
            
            return None
    
    def extract_transaction_data(self, template: BankEmailTemplate, email_body: str) -> Dict:
        """
        Extract transaction data using the specified template.
        Updates template performance metrics.
        """        
        extraction_result = template.extract_data(email_body)
        
        # Update template performance in a separate session to avoid detached instance issues
        with DatabaseSession() as db:
            # Reload template in current session to avoid detached instance error
            fresh_template = db.query(BankEmailTemplate).get(template.id)
            if fresh_template:
                # Update template performance
                if extraction_result['confidence_score'] > 0.5:
                    fresh_template.success_count += 1
                    fresh_template.last_success_at = datetime.utcnow()
                    # Update rolling average confidence
                    old_avg = fresh_template.avg_confidence_score
                    new_count = fresh_template.success_count
                    fresh_template.avg_confidence_score = ((old_avg * (new_count - 1)) + extraction_result['confidence_score']) / new_count
                else:
                    fresh_template.failure_count += 1
                
                db.commit()
        
        return extraction_result
    
    def auto_generate_template(self, bank_id: int, sample_emails: List[EmailParsingJob], template_type: str = None) -> Optional[int]:
        """
        Automatically generate a new template using AI based on sample emails.
        Includes protection against duplicate template generation.
        Returns template ID (not object) to avoid session issues.
        """
        if not sample_emails:
            logger.error("No sample emails provided for template generation")
            return None

        with DatabaseSession() as db:
            bank = db.query(Bank).filter(Bank.id == bank_id).first()
            if not bank:
                logger.error(f"Bank with id={bank_id} not found")
                return None

            # PROTECTION: Check again for existing templates to prevent race conditions
            # This prevents multiple workers from generating templates simultaneously
            existing_templates = db.query(BankEmailTemplate).filter(
                BankEmailTemplate.bank_id == bank_id,
                BankEmailTemplate.is_active == True
            ).all()
            
            if existing_templates:
                logger.info(f"Templates already exist for {bank.name}, returning first one")
                # Return the first existing template ID
                return existing_templates[0].id

            logger.info(f"Generating new template for {bank.name} with {len(sample_emails)} sample emails")
            
            # Prepare email samples for AI
            email_samples = []
            for job in sample_emails[:5]:  # Use up to 5 samples
                email_samples.append({
                    'subject': job.email_subject or '',
                    'sender': job.email_from or '',
                    'body': job.email_body[:2000]  # Limit body size
                })

            # Generate template using AI
            ai_service = self._get_ai_service()
            if not ai_service:
                logger.error("AI service not available - cannot generate template")
                return None

            ai_result = self._generate_ai_template(bank.name, email_samples, template_type)
            if not ai_result:
                logger.error("AI template generation failed")
                return None

            # Create new template
            template = BankEmailTemplate(
                bank_id=bank_id,
                template_name=ai_result['template_name'],
                template_type=ai_result['template_type'],
                description=ai_result['description'],
                subject_pattern=ai_result.get('subject_pattern'),
                sender_pattern=ai_result.get('sender_pattern'),
                body_contains=ai_result.get('body_contains'),
                body_excludes=ai_result.get('body_excludes'),
                amount_regex=ai_result['amount_regex'],
                description_regex=ai_result.get('description_regex'),
                date_regex=ai_result.get('date_regex'),
                merchant_regex=ai_result.get('merchant_regex'),
                reference_regex=ai_result.get('reference_regex'),
                priority=ai_result.get('priority', 50),
                confidence_threshold=0.6,
                generation_method='ai_generated',
                ai_model_used=ai_result.get('ai_model', 'gpt-4'),
                ai_prompt_used=ai_result.get('prompt_used'),
                training_emails_count=len(sample_emails),
                training_emails_sample=[job.id for job in sample_emails],
                test_email_body=sample_emails[0].email_body[:1000] if sample_emails else None,
                created_at=datetime.utcnow()
            )

            db.add(template)
            db.commit()
            db.refresh(template)

            template_id = template.id
            template_name = template.template_name
            
            logger.info(f"Created new template: {template_name} (ID: {template_id})")
            return template_id
    
    def _generate_ai_template(self, bank_name: str, email_samples: List[Dict], template_type: str = None) -> Optional[Dict]:
        """
        Use AI to analyze email samples and generate template patterns.
        """
        try:
            # Prepare prompt for AI
            prompt = f"""
            Analyze these {bank_name} banking emails and create a comprehensive email template for automatic transaction extraction.
            
            Email samples:
            """
            
            for i, sample in enumerate(email_samples, 1):
                prompt += f"\n--- Sample {i} ---\n"
                prompt += f"Subject: {sample['subject']}\n"
                prompt += f"Sender: {sample['sender']}\n"
                prompt += f"Body: {sample['body'][:800]}...\n"
            
            prompt += """
            
            Create a JSON response with the following template structure:
            {
                "template_name": "Descriptive name for this email type",
                "template_type": "purchase|withdrawal|transfer|deposit|payment|fee",
                "description": "Human readable description",
                "subject_pattern": "Regex pattern to match email subjects (optional)",
                "sender_pattern": "Regex pattern to match sender email (optional)",
                "body_contains": ["keyword1", "keyword2"] (required keywords in body),
                "body_excludes": ["excluded1", "excluded2"] (keywords that exclude this template),
                "amount_regex": "Regex with named group (?P<amount>...)",
                "description_regex": "Regex with named group (?P<description>...)",
                "date_regex": "Regex with named group (?P<date>...)",
                "merchant_regex": "Regex with named group (?P<merchant>...)",
                "reference_regex": "Regex with named group (?P<reference>...)",
                "priority": 50
            }
            
            Requirements:
            - Use named groups in regex patterns: (?P<fieldname>...)
            - Make patterns flexible to handle variations
            - Include currency patterns (like CRC, USD, etc.)
            - Handle number formatting (commas, decimals)
            - Return valid JSON only
            """
            
            # Get AI service
            ai_service = self._get_ai_service()
            if not ai_service:
                logger.error("AI service not available")
                return None
            
            # Call AI service
            response = ai_service.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing banking emails and creating extraction patterns. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1500
            )
            
            # Parse AI response
            import json
            ai_response = response.choices[0].message.content.strip()
            
            # Clean JSON response
            if ai_response.startswith('```json'):
                ai_response = ai_response[7:]
            if ai_response.endswith('```'):
                ai_response = ai_response[:-3]
            
            template_data = json.loads(ai_response)
            template_data['ai_model'] = "gpt-4"
            template_data['prompt_used'] = prompt[:500] + "..."
            
            # Validate required fields
            required_fields = ['template_name', 'template_type', 'amount_regex']
            for field in required_fields:
                if field not in template_data:
                    logger.error(f"AI response missing required field: {field}")
                    return None
            
            return template_data
            
        except Exception as e:
            logger.error(f"AI template generation error: {e}")
            return None
    
    def validate_template(self, template: BankEmailTemplate, test_emails: List[EmailParsingJob]) -> Dict:
        """
        Validate template performance against test emails.
        Returns validation metrics.
        """
        results = {
            'total_tested': len(test_emails),
            'successful_extractions': 0,
            'failed_extractions': 0,
            'avg_confidence': 0.0,
            'extraction_samples': []
        }
        
        confidence_scores = []
        
        for email in test_emails:
            match_score = template.calculate_match_score(
                email.email_subject or '',
                email.email_from or '',
                email.email_body or ''
            )
            
            if match_score >= template.confidence_threshold:
                extraction = template.extract_data(email.email_body or '')
                confidence_scores.append(extraction['confidence_score'])
                
                if extraction['confidence_score'] > 0.5:
                    results['successful_extractions'] += 1
                else:
                    results['failed_extractions'] += 1
                
                # Store sample for review
                if len(results['extraction_samples']) < 3:
                    results['extraction_samples'].append({
                        'email_id': email.id,
                        'match_score': match_score,
                        'extraction': extraction
                    })
            else:
                results['failed_extractions'] += 1
        
        results['avg_confidence'] = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        return results
    
    def get_templates_for_bank(self, bank_id: int) -> List[BankEmailTemplate]:
        """
        Get all templates for a specific bank, ordered by priority.
        """
        with DatabaseSession() as db:
            return db.query(BankEmailTemplate).filter(
                BankEmailTemplate.bank_id == bank_id
            ).order_by(desc(BankEmailTemplate.priority)).all()
    
    def optimize_template_priorities(self, bank_id: int):
        """
        Optimize template priorities based on success rates and usage frequency.
        """
        with DatabaseSession() as db:
            templates = db.query(BankEmailTemplate).filter(
                BankEmailTemplate.bank_id == bank_id,
                BankEmailTemplate.is_active == True
            ).all()
            
            # Calculate scores and sort
            template_scores = []
            for template in templates:
                total_attempts = template.success_count + template.failure_count
                if total_attempts > 0:
                    success_rate = template.success_count / total_attempts
                    # Combine success rate with confidence and usage frequency
                    score = (success_rate * 0.5) + (template.avg_confidence_score * 0.3) + (min(total_attempts / 100, 1.0) * 0.2)
                else:
                    score = 0.0
                
                template_scores.append((template, score))
            
            # Sort by score descending
            template_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Update priorities
            for i, (template, score) in enumerate(template_scores):
                template.priority = 100 - (i * 10)  # Higher priority for better templates
            
            db.commit()
            logger.info(f"Optimized priorities for {len(templates)} templates in bank_id={bank_id}")
    
    def cleanup_obsolete_templates(self, bank_id: int, min_success_rate: float = 0.1):
        """
        Deactivate templates with consistently poor performance.
        """
        with DatabaseSession() as db:
            templates = db.query(BankEmailTemplate).filter(
                BankEmailTemplate.bank_id == bank_id,
                BankEmailTemplate.is_active == True
            ).all()
            
            deactivated = 0
            for template in templates:
                total_attempts = template.success_count + template.failure_count
                if total_attempts >= 10:  # Only consider templates with enough data
                    success_rate = template.success_count / total_attempts
                    if success_rate < min_success_rate:
                        template.is_active = False
                        deactivated += 1
                        logger.info(f"Deactivated low-performing template: {template.template_name} (success rate: {success_rate:.2f})")
            
            if deactivated > 0:
                db.commit()
                logger.info(f"Deactivated {deactivated} obsolete templates for bank_id={bank_id}") 