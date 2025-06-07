import os
import json
import re
import logging
from datetime import datetime, UTC
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI

# Add HTML parsing support
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from ..models.bank import Bank
from ..models.parsing_rule import ParsingRule
from ..models.email_parsing_job import EmailParsingJob
from ..core.database import db


class AIRuleGeneratorService:
    """
    Enhanced AI service for generating robust parsing rules using OpenAI GPT.
    
    Features:
    - Automatic retry with improved prompts if regex fails
    - Immediate validation against sample emails
    - HTML content parsing for email bodies
    - Smart validation to detect meaningless extractions
    - Generic prompts for any bank worldwide
    - Confidence scoring and quality assessment
    - Fallback patterns for common banking data
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"AIRuleGenerator")
        
        # Initialize OpenAI client
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        
        # Configuration
        self.max_retries = 3
        self.min_success_rate = 0.5  # At least 50% of emails must match
        self.max_sample_emails = 5
        
        # HTML parsing warning
        if BeautifulSoup is None:
            self.logger.warning("BeautifulSoup not available. HTML emails will be processed as raw text.")
        
        # Invalid extraction patterns (to detect meaningless results)
        self.invalid_patterns = [
            r'^(DOCTYPE|html|head|body|meta|script|style).*',  # HTML tags
            r'^\s*0+\s*$',  # Just zeros
            r'^[<>]+$',  # Just brackets
            r'^[\s\-_\.]+$',  # Just whitespace/punctuation
            r'^(null|undefined|none|N/A)$',  # Null values
        ]
        
        # Fallback patterns for common banking data
        self.fallback_patterns = {
            'amount': [
                r'(?P<amount>[\$€£¥₡₹₽₦₨₪₴₵₢₡]?\s*[\d,]+\.?\d*)',  # Currency symbols + numbers
                r'(?P<amount>\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b)',    # Standard monetary format
                r'(?P<amount>(?:USD|EUR|CRC|USD|GBP|JPY)\s*[\d,]+\.?\d*)', # Currency codes
            ],
            'date': [
                r'(?P<date>\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',           # DD/MM/YYYY or MM/DD/YYYY
                r'(?P<date>\d{4}[/-]\d{1,2}[/-]\d{1,2})',             # YYYY/MM/DD
                r'(?P<date>\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4})', # DD Mon YYYY
            ],
            'description': [
                r'(?P<description>(?:Transfer|Payment|Purchase|Deposit|Withdrawal|ATM|POS)[\w\s]+)',
                r'(?P<description>(?:Merchant|Store|Company):\s*([^\n\r,;]+))',
                r'(?P<description>Description:\s*([^\n\r,;]+))',
            ]
        }
        
        self.logger.info(f"Enhanced AIRuleGeneratorService initialized with model: {self.model}")
    
    def generate_parsing_rules_for_bank(self, bank_id: int, sample_emails: List[EmailParsingJob]) -> List[ParsingRule]:
        """
        Generate parsing rules for any bank using sample emails with automatic retry and validation.
        
        Args:
            bank_id: ID of the bank to generate rules for
            sample_emails: List of EmailParsingJob objects to analyze
            
        Returns:
            List of validated ParsingRule objects that actually work
        """
        try:
            bank = db.session.query(Bank).get(bank_id)
            if not bank:
                raise ValueError(f"Bank with ID {bank_id} not found")
            
            self.logger.info(f"Generating parsing rules for bank: {bank.name}")
            
            # Limit and prepare email samples
            limited_samples = sample_emails[:self.max_sample_emails]
            email_samples = self._prepare_email_samples(limited_samples)
            
            # Generate rules with retry mechanism
            validated_rules = []
            
            for attempt in range(1, self.max_retries + 1):
                self.logger.info(f"Generation attempt {attempt}/{self.max_retries} for {bank.name}")
                
                try:
                    # Generate rules using AI
                    generated_rules_data = self._call_openai_api(bank.name, email_samples, attempt)
                    
                    # Convert to ParsingRule objects
                    parsing_rules = self._create_parsing_rules_from_ai_response(
                        bank_id, 
                        generated_rules_data, 
                        limited_samples,
                        attempt
                    )
                    
                    # Validate rules immediately
                    validated_rules = self._validate_rules_with_scoring(parsing_rules, limited_samples)
                    
                    if validated_rules:
                        self.logger.info(f"Success! Generated {len(validated_rules)} working rules for {bank.name}")
                        break
                    else:
                        self.logger.warning(f"Attempt {attempt} generated rules but none passed validation")
                        
                except Exception as e:
                    self.logger.error(f"Attempt {attempt} failed: {str(e)}")
                    if attempt == self.max_retries:
                        # Final attempt - try fallback patterns
                        self.logger.info("Trying fallback patterns as last resort")
                        validated_rules = self._generate_fallback_rules(bank_id, limited_samples)
            
            # Save validated rules to database
            if validated_rules:
                self._save_rules_to_database(validated_rules)
                self.logger.info(f"Saved {len(validated_rules)} validated parsing rules for {bank.name}")
            else:
                self.logger.error(f"Failed to generate any working rules for {bank.name}")
            
            return validated_rules
            
        except Exception as e:
            self.logger.error(f"Error generating parsing rules for bank {bank_id}: {str(e)}")
            raise
    
    def _prepare_email_samples(self, sample_emails: List[EmailParsingJob]) -> List[Dict]:
        """Prepare email samples for AI analysis with HTML parsing"""
        email_samples = []
        
        for email_job in sample_emails:
            # Parse email body - handle HTML content
            body = self._parse_email_body(email_job.email_body) if email_job.email_body else ""
            subject = email_job.email_subject[:200] if email_job.email_subject else ""
            
            email_samples.append({
                'sender': email_job.email_from or "unknown@bank.com",
                'subject': subject,
                'body': body[:3000],  # Limit after parsing
                'email_id': email_job.id,
                'original_length': len(email_job.email_body) if email_job.email_body else 0
            })
        
        return email_samples
    
    def _parse_email_body(self, email_body: str) -> str:
        """Parse email body, extracting text from HTML if needed"""
        if not email_body:
            return ""
        
        # Check if content is HTML
        if self._is_html_content(email_body):
            return self._extract_text_from_html(email_body)
        else:
            return email_body
    
    def _is_html_content(self, content: str) -> bool:
        """Check if content contains HTML"""
        html_indicators = ['<!DOCTYPE', '<html', '<head>', '<body>', '<div', '<span', '<p>']
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in html_indicators)
    
    def _extract_text_from_html(self, html_content: str) -> str:
        """Extract clean text from HTML content"""
        if BeautifulSoup is None:
            # Fallback: simple regex cleanup
            self.logger.warning("BeautifulSoup not available, using simple HTML cleanup")
            
            # Remove script and style elements
            text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
            
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', ' ', text)
            
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            
            return text
        else:
            # Use BeautifulSoup for proper HTML parsing
            try:
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Extract text
                text = soup.get_text()
                
                # Clean up whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                
                return text
                
            except Exception as e:
                self.logger.error(f"Error parsing HTML with BeautifulSoup: {str(e)}")
                # Fallback to simple cleanup
                return self._extract_text_from_html(html_content)
    
    def _call_openai_api(self, bank_name: str, email_samples: List[Dict], attempt: int) -> Dict[str, Any]:
        """
        Call OpenAI API with enhanced prompts based on attempt number.
        """
        try:
            # Create adaptive prompt based on attempt
            prompt = self._create_adaptive_ai_prompt(bank_name, email_samples, attempt)
            
            self.logger.info(f"Calling OpenAI API (attempt {attempt}) with {len(email_samples)} email samples")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert regex engineer specializing in extracting transaction data from banking emails worldwide.
                        
                        CRITICAL REQUIREMENTS:
                        1. Return ONLY valid JSON with the exact structure requested
                        2. Use named capture groups for all extractions
                        3. Make patterns robust to handle variations in formatting
                        4. Test your regex mentally before returning
                        5. Handle multiple currencies, date formats, and languages
                        6. No explanations, only JSON"""
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.1 if attempt == 1 else 0.3,  # Increase creativity on retries
                max_tokens=3000
            )
            
            # Parse and validate response
            response_content = response.choices[0].message.content.strip()
            parsed_response = self._parse_ai_response(response_content)
            
            self.logger.info(f"Successfully received AI response for attempt {attempt}")
            return parsed_response
                
        except Exception as e:
            self.logger.error(f"Error calling OpenAI API (attempt {attempt}): {str(e)}")
            raise
    
    def _create_adaptive_ai_prompt(self, bank_name: str, email_samples: List[Dict], attempt: int) -> str:
        """Create adaptive prompt that improves with each retry attempt"""
        
        base_prompt = f"""
Analyze these banking emails from {bank_name} and create robust regex patterns to extract transaction data.

SAMPLE EMAILS:
"""
        
        for i, email in enumerate(email_samples, 1):
            base_prompt += f"""
EMAIL {i}:
From: {email['sender']}
Subject: {email['subject']}
Body: {email['body'][:1500]}
---
"""
        
        # Adaptive instructions based on attempt
        if attempt == 1:
            instructions = """
Create regex patterns to extract these fields (only extract what's clearly present):
- amount: Transaction amount with currency (use named group: (?P<amount>...))
- date: Transaction date in any format (use named group: (?P<date>...))  
- description: Transaction description/merchant (use named group: (?P<description>...))
- source: Transaction source/account if available (use named group: (?P<source>...))
- from_bank: Originating bank for transfers (use named group: (?P<from_bank>...))
- to_bank: Destination bank for transfers (use named group: (?P<to_bank>...))

CRITICAL REGEX SYNTAX RULES:
- Use ONLY named capture groups: (?P<fieldname>pattern)
- NO nested parentheses inside named groups
- NO square brackets around entire patterns
- Test your regex mentally before submitting

CORRECT EXAMPLES:
- Amount: (?P<amount>CRC\\s\\d{1,3}(?:,\\d{3})*(?:\\.\\d{2})?)
- Date: (?P<date>\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4})
- Description: (?P<description>Comercio:\\s+([A-Z][A-Z\\s]*))

WRONG EXAMPLES (DO NOT USE):
- (?P<amount>CRC\\s[\\d{1,3}(?:,\\d{3})*]) ← Square brackets wrong
- (?P<description>Comercio:\\s([A-Z\\s]+)) ← Nested parentheses wrong

IMPORTANT: Use single backslashes in your regex patterns. The JSON parser will handle escaping.
"""
        elif attempt == 2:
            instructions = """
SECOND ATTEMPT - Previous patterns failed validation. Be more flexible:

- amount: Look for ANY numeric pattern with currency symbols, codes, or decimal formats
- date: Accept ANY date format (DD/MM/YY, MM-DD-YYYY, Month DD, YYYY, etc.)
- description: Extract ANY descriptive text about the transaction
- source: Look for account numbers, card numbers, or source identifiers
- from_bank/to_bank: Extract bank names or codes from transfer details

CRITICAL:
- Use broader, more flexible patterns
- Include optional elements with ?
- Use \\s* for flexible whitespace
- Consider multi-line matching with (?s) flag
"""
        else:  # attempt 3+
            instructions = """
FINAL ATTEMPT - Use maximum flexibility and multiple alternative patterns:

For each field, provide 2-3 alternative regex patterns that match different formats.
Be extremely permissive - better to extract something than nothing.

EXAMPLES:
- amount: Match "1,234.56", "$1234", "USD 1,234", "₡500", etc.
- date: Match "2024-01-01", "01/01/24", "Jan 1, 2024", "1-Jan-2024", etc.
- description: Match anything after keywords like "Payment", "Transfer", "Purchase"

Use (.*?) for very broad matching when needed.
"""
        
        json_structure = """
Return EXACTLY this JSON structure:
{
    "rules": [
        {
            "rule_name": "Amount Pattern",
            "rule_type": "amount",
            "regex_pattern": "(?P<amount>your_pattern_here)",
            "description": "Extracts transaction amount",
            "example_input": "actual text from email that should match",
            "example_output": "expected extracted value",
            "priority": 10,
            "confidence_estimate": 0.8
        },
        {
            "rule_name": "Date Pattern", 
            "rule_type": "date",
            "regex_pattern": "(?P<date>your_pattern_here)",
            "description": "Extracts transaction date",
            "example_input": "actual text from email that should match",
            "example_output": "expected extracted value",
            "priority": 9,
            "confidence_estimate": 0.7
        },
        {
            "rule_name": "Description Pattern",
            "rule_type": "description",
            "regex_pattern": "(?P<description>your_pattern_here)",
            "description": "Extracts transaction description",
            "example_input": "actual text from email that should match",
            "example_output": "expected extracted value",
            "priority": 8,
            "confidence_estimate": 0.9
        }
    ]
}
"""
        
        return base_prompt + instructions + json_structure
    
    def _parse_ai_response(self, response_content: str) -> Dict[str, Any]:
        """Parse and validate AI response"""
        try:
            # Extract JSON from response
            if '```json' in response_content:
                json_start = response_content.find('```json') + 7
                json_end = response_content.find('```', json_start)
                response_content = response_content[json_start:json_end].strip()
            elif '```' in response_content:
                json_start = response_content.find('```') + 3
                json_end = response_content.find('```', json_start)
                response_content = response_content[json_start:json_end].strip()
            
            # Fix common JSON escape issues from AI
            response_content = self._fix_json_escapes(response_content)
            
            parsed_response = json.loads(response_content)
            
            # Validate structure
            if 'rules' not in parsed_response:
                raise ValueError("Response missing 'rules' key")
            
            if not isinstance(parsed_response['rules'], list):
                raise ValueError("'rules' must be a list")
            
            return parsed_response
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse AI response as JSON: {str(e)}")
            self.logger.error(f"Raw response: {response_content}")
            raise ValueError(f"Invalid JSON response from AI: {str(e)}")
    
    def _fix_json_escapes(self, json_content: str) -> str:
        """Fix common JSON escape issues from AI responses"""
        # Fix double backslashes in regex patterns
        # Replace \\d, \\s, \\w etc. with \d, \s, \w
        import re
        fixed_content = re.sub(r'\\\\([dswDSW])', r'\\\1', json_content)
        
        # Fix other common double escapes
        fixed_content = re.sub(r'\\\\([.])', r'\\\1', fixed_content)
        
        return fixed_content
    
    def _create_parsing_rules_from_ai_response(
        self, 
        bank_id: int, 
        ai_response: Dict[str, Any], 
        sample_emails: List[EmailParsingJob],
        attempt: int
    ) -> List[ParsingRule]:
        """Convert AI response to ParsingRule objects with enhanced metadata"""
        
        parsing_rules = []
        
        try:
            rules_data = ai_response.get('rules', [])
            
            for rule_data in rules_data:
                # Validate regex pattern before creating rule
                regex_pattern = rule_data.get('regex_pattern', '')
                if not self._validate_regex_pattern(regex_pattern):
                    self.logger.warning(f"Skipping invalid regex pattern: {regex_pattern}")
                    continue
                
                # Calculate base confidence from AI estimate and attempt
                ai_confidence = rule_data.get('confidence_estimate', 0.5)
                attempt_penalty = (attempt - 1) * 0.1  # Reduce confidence for later attempts
                base_confidence = max(0.1, ai_confidence - attempt_penalty)
                
                parsing_rule = ParsingRule(
                    bank_id=bank_id,
                    rule_name=rule_data.get('rule_name', f'AI Generated {rule_data.get("rule_type", "Unknown")}'),
                    rule_type=rule_data.get('rule_type', 'unknown'),
                    regex_pattern=regex_pattern,
                    description=rule_data.get('description', 'AI generated rule'),
                    example_input=rule_data.get('example_input', ''),
                    example_output=rule_data.get('example_output', ''),
                    priority=rule_data.get('priority', 5),
                    
                    # Enhanced AI metadata
                    generation_method='ai_generated_enhanced',
                    ai_model_used=self.model,
                    ai_prompt_used=f"Enhanced prompt (attempt {attempt})",
                    training_emails_count=len(sample_emails),
                    training_emails_sample=[{
                        'id': email.id,
                        'sender': email.email_from,
                        'subject': email.email_subject[:100] if email.email_subject else ''
                    } for email in sample_emails[:3]],
                    
                    # Configuration
                    is_active=True,
                    confidence_boost=base_confidence,
                    created_by=f'AI_SERVICE_v2_attempt_{attempt}',
                    success_count=0,
                    failure_count=0,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC)
                )
                
                parsing_rules.append(parsing_rule)
                
        except Exception as e:
            self.logger.error(f"Error creating parsing rules from AI response: {str(e)}")
            raise
            
        return parsing_rules
    
    def _validate_regex_pattern(self, pattern: str) -> bool:
        """Validate regex pattern syntax and structure"""
        try:
            # Basic compilation test
            compiled_pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            
            # Additional structural validation
            if not self._is_well_formed_regex(pattern):
                self.logger.warning(f"Regex pattern has structural issues: {pattern}")
                return False
            
            return True
        except re.error as e:
            self.logger.error(f"Regex compilation error: {e}")
            return False
    
    def _is_well_formed_regex(self, pattern: str) -> bool:
        """Check if regex follows our structural requirements"""
        
        # Must contain a named group
        if not re.search(r'\(\?P<\w+>', pattern):
            return False
        
        # Should not have common problematic patterns
        problematic_patterns = [
            r'\[\w+\{',  # Square brackets with quantifiers inside
            r'\(\?P<\w+>[^)]*\([^)]*\)[^)]*\)',  # Nested parentheses in named groups (simple check)
        ]
        
        for problematic in problematic_patterns:
            if re.search(problematic, pattern):
                self.logger.debug(f"Found problematic pattern: {problematic}")
                return False
        
        return True
    
    def _validate_rules_with_scoring(
        self, 
        parsing_rules: List[ParsingRule], 
        test_emails: List[EmailParsingJob]
    ) -> List[ParsingRule]:
        """
        Validate generated rules against test emails with enhanced validation.
        Only return rules that extract meaningful data.
        """
        
        validated_rules = []
        
        for rule in parsing_rules:
            try:
                # Test regex pattern
                pattern = re.compile(rule.regex_pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                
                # Test against all sample emails
                matches_found = 0
                total_emails = len(test_emails)
                meaningful_extractions = []
                
                for email in test_emails:
                    try:
                        # Parse email body first
                        clean_body = self._parse_email_body(email.email_body)
                        
                        match = pattern.search(clean_body)
                        if match:
                            # Try to extract named group for this rule type
                            extracted_value = match.groupdict().get(rule.rule_type)
                            if extracted_value and self._is_meaningful_extraction(extracted_value, rule.rule_type):
                                matches_found += 1
                                meaningful_extractions.append({
                                    'email_id': email.id,
                                    'extracted': extracted_value.strip(),
                                    'full_match': match.group(0)[:100]
                                })
                    except Exception as e:
                        self.logger.debug(f"Match error for rule {rule.rule_name}: {str(e)}")
                        continue
                
                # Calculate success rate
                success_rate = matches_found / total_emails if total_emails > 0 else 0
                
                # Only keep rules that meet minimum success rate AND have meaningful extractions
                if success_rate >= self.min_success_rate and meaningful_extractions:
                    # Update rule metadata with validation results
                    rule.success_count = matches_found
                    rule.confidence_boost = min(0.9, rule.confidence_boost + (success_rate * 0.3))
                    
                    # Store validation metadata
                    rule.example_input = meaningful_extractions[0]['full_match'] if meaningful_extractions else rule.example_input
                    rule.example_output = meaningful_extractions[0]['extracted'] if meaningful_extractions else rule.example_output
                    
                    validated_rules.append(rule)
                    
                    self.logger.info(f"✅ Rule '{rule.rule_name}' validated: {matches_found}/{total_emails} emails matched ({success_rate:.1%})")
                else:
                    # Log why rule failed
                    if not meaningful_extractions:
                        self.logger.warning(f"❌ Rule '{rule.rule_name}' failed: no meaningful extractions found")
                    else:
                        self.logger.warning(f"❌ Rule '{rule.rule_name}' failed validation: {matches_found}/{total_emails} emails matched ({success_rate:.1%})")
                    
            except Exception as e:
                self.logger.error(f"Error validating rule {rule.rule_name}: {str(e)}")
                continue
        
        self.logger.info(f"Validation complete: {len(validated_rules)}/{len(parsing_rules)} rules passed")
        return validated_rules
    
    def _is_meaningful_extraction(self, extracted_value: str, rule_type: str) -> bool:
        """Check if extracted value is meaningful (not HTML artifacts or meaningless data)"""
        if not extracted_value or len(extracted_value.strip()) < 1:
            return False
        
        cleaned_value = extracted_value.strip()
        
        # Check against invalid patterns
        for invalid_pattern in self.invalid_patterns:
            if re.match(invalid_pattern, cleaned_value, re.IGNORECASE):
                self.logger.debug(f"Invalid extraction detected: '{cleaned_value}' matches pattern {invalid_pattern}")
                return False
        
        # Rule-specific validation
        if rule_type == 'amount':
            # Amount should contain digits and be reasonable
            if not re.search(r'\d', cleaned_value):
                return False
            # Extract just numbers to check if reasonable
            numbers = re.findall(r'\d+', cleaned_value)
            if numbers:
                try:
                    amount = float(''.join(numbers))
                    # Reject unreasonable amounts (too small or too large)
                    if amount < 0.01 or amount > 999999999:
                        return False
                except ValueError:
                    return False
        
        elif rule_type == 'date':
            # Date should contain digits and date-like patterns
            if not re.search(r'\d', cleaned_value):
                return False
            if len(cleaned_value) < 4:  # Too short to be a date
                return False
        
        elif rule_type == 'description':
            # Description should be meaningful text, not HTML
            if len(cleaned_value) < 3:  # Too short
                return False
            if re.match(r'^[^a-zA-Z]*$', cleaned_value):  # No letters
                return False
        
        return True
    
    def _generate_fallback_rules(self, bank_id: int, sample_emails: List[EmailParsingJob]) -> List[ParsingRule]:
        """Generate fallback rules using predefined patterns when AI fails"""
        
        self.logger.info("Generating fallback rules with predefined patterns")
        fallback_rules = []
        
        for rule_type, patterns in self.fallback_patterns.items():
            for i, pattern in enumerate(patterns):
                rule = ParsingRule(
                    bank_id=bank_id,
                    rule_name=f'Fallback {rule_type.title()} Pattern {i+1}',
                    rule_type=rule_type,
                    regex_pattern=pattern,
                    description=f'Fallback pattern for {rule_type} extraction',
                    priority=1,  # Lower priority than AI rules
                    
                    generation_method='fallback_pattern',
                    ai_model_used=None,
                    training_emails_count=len(sample_emails),
                    
                    is_active=True,
                    confidence_boost=0.2,  # Lower confidence for fallback
                    created_by='FALLBACK_SYSTEM',
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC)
                )
                
                fallback_rules.append(rule)
        
        # Validate fallback rules
        validated_fallback = self._validate_rules_with_scoring(fallback_rules, sample_emails)
        
        self.logger.info(f"Generated {len(validated_fallback)} working fallback rules")
        return validated_fallback
    
    def _save_rules_to_database(self, rules: List[ParsingRule]) -> None:
        """Save validated rules to database"""
        try:
            for rule in rules:
                db.session.add(rule)
            
            db.session.commit()
            self.logger.info(f"Successfully saved {len(rules)} rules to database")
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error saving rules to database: {str(e)}")
            raise
    
    def test_rule_against_emails(
        self, 
        rule: ParsingRule, 
        test_emails: List[EmailParsingJob]
    ) -> Tuple[float, List[Dict]]:
        """
        Test a specific rule against emails and return success rate and extractions.
        Useful for debugging and rule improvement.
        """
        try:
            pattern = re.compile(rule.regex_pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            
            successful_extractions = []
            
            for email in test_emails:
                try:
                    match = pattern.search(email.email_body)
                    if match:
                        extracted_value = match.groupdict().get(rule.rule_type)
                        if extracted_value:
                            successful_extractions.append({
                                'email_id': email.id,
                                'extracted': extracted_value.strip(),
                                'full_match': match.group(0)[:200],
                                'email_subject': email.email_subject[:100]
                            })
                except Exception:
                    continue
            
            success_rate = len(successful_extractions) / len(test_emails) if test_emails else 0
            
            return success_rate, successful_extractions
            
        except Exception as e:
            self.logger.error(f"Error testing rule: {str(e)}")
            return 0.0, [] 