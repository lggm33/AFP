from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class BankEmailTemplate(Base):
    __tablename__ = "bank_email_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    bank_id = Column(Integer, ForeignKey("banks.id"), nullable=False, index=True)
    
    # Template identification
    template_name = Column(String(255), nullable=False, index=True)  # "Debit Card Purchase", "ATM Withdrawal", "Transfer Sent"
    template_type = Column(String(100), nullable=False, index=True)  # "purchase", "withdrawal", "transfer", "deposit", "payment"
    description = Column(Text, nullable=True)  # Human-readable description
    
    # Email patterns for identification
    subject_pattern = Column(Text, nullable=True)  # Regex pattern to match email subjects
    sender_pattern = Column(Text, nullable=True)  # Regex pattern to match sender email
    body_contains = Column(JSON, nullable=True)  # Keywords that must be present in email body
    body_excludes = Column(JSON, nullable=True)  # Keywords that exclude this template
    
    # Extraction patterns
    amount_regex = Column(Text, nullable=False)  # Regex to extract amount
    description_regex = Column(Text, nullable=True)  # Regex to extract transaction description
    date_regex = Column(Text, nullable=True)  # Regex to extract date
    merchant_regex = Column(Text, nullable=True)  # Regex to extract merchant/location
    reference_regex = Column(Text, nullable=True)  # Regex to extract reference number
    
    # Template configuration
    priority = Column(Integer, default=0, nullable=False, index=True)  # Template matching priority (higher = first)
    confidence_threshold = Column(Float, default=0.7, nullable=False)  # Minimum confidence to use this template
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # AI generation metadata
    generation_method = Column(String(50), default="manual", nullable=False)  # "manual", "ai_generated", "ai_refined"
    ai_model_used = Column(String(100), nullable=True)  # "gpt-4", "claude-3", etc.
    ai_prompt_used = Column(Text, nullable=True)  # Prompt used to generate the template
    training_emails_count = Column(Integer, default=0, nullable=False)  # Number of emails used for training
    training_emails_sample = Column(JSON, nullable=True)  # Sample of training emails (IDs or excerpts)
    
    # Performance tracking
    success_count = Column(Integer, default=0, nullable=False)  # Times successfully applied
    failure_count = Column(Integer, default=0, nullable=False)  # Times failed to extract data
    avg_confidence_score = Column(Float, default=0.0, nullable=False)  # Average confidence of extractions
    last_success_at = Column(DateTime, nullable=True)  # Last successful extraction
    
    # Validation examples
    test_email_body = Column(Text, nullable=True)  # Sample email body for testing
    expected_amount = Column(String(50), nullable=True)  # Expected amount extraction
    expected_description = Column(String(500), nullable=True)  # Expected description extraction
    expected_date = Column(String(50), nullable=True)  # Expected date extraction
    
    # Timestamps
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    
    # Relationships
    bank = relationship("Bank", back_populates="email_templates")
    
    def __repr__(self):
        return f"<BankEmailTemplate(id={self.id}, bank_id={self.bank_id}, name='{self.template_name}', type='{self.template_type}')>"
    
    def calculate_match_score(self, email_subject, email_sender, email_body):
        """
        Calculate how well this template matches an email.
        Returns a score from 0.0 to 1.0
        """
        score = 0.0
        total_checks = 0
        
        # Check subject pattern
        if self.subject_pattern:
            import re
            total_checks += 1
            if re.search(self.subject_pattern, email_subject or "", re.IGNORECASE):
                score += 0.3
        
        # Check sender pattern
        if self.sender_pattern:
            total_checks += 1
            if re.search(self.sender_pattern, email_sender or "", re.IGNORECASE):
                score += 0.2
        
        # Check required keywords
        if self.body_contains:
            total_checks += 1
            contains_all = all(
                keyword.lower() in (email_body or "").lower() 
                for keyword in self.body_contains
            )
            if contains_all:
                score += 0.3
        
        # Check excluded keywords (penalty)
        if self.body_excludes:
            total_checks += 1
            excludes_none = not any(
                keyword.lower() in (email_body or "").lower() 
                for keyword in self.body_excludes
            )
            if excludes_none:
                score += 0.2
            else:
                score = 0.0  # Immediate disqualification
        
        # Normalize score
        if total_checks > 0:
            return min(score, 1.0)
        return 0.0
    
    def extract_data(self, email_body):
        """
        Extract transaction data from email body using this template's patterns.
        Returns dict with extracted data and confidence score.
        """
        import re
        extracted = {}
        confidence_scores = []
        
        # Extract amount
        if self.amount_regex and email_body:
            match = re.search(self.amount_regex, email_body, re.IGNORECASE)
            if match:
                extracted['amount'] = match.group('amount') if 'amount' in match.groupdict() else match.group(1)
                confidence_scores.append(0.9)
            else:
                confidence_scores.append(0.0)
        
        # Extract description
        if self.description_regex and email_body:
            match = re.search(self.description_regex, email_body, re.IGNORECASE)
            if match:
                extracted['description'] = match.group('description') if 'description' in match.groupdict() else match.group(1)
                confidence_scores.append(0.8)
            else:
                confidence_scores.append(0.0)
        
        # Extract date
        if self.date_regex and email_body:
            match = re.search(self.date_regex, email_body, re.IGNORECASE)
            if match:
                extracted['date'] = match.group('date') if 'date' in match.groupdict() else match.group(1)
                confidence_scores.append(0.7)
            else:
                confidence_scores.append(0.0)
        
        # Extract merchant
        if self.merchant_regex and email_body:
            match = re.search(self.merchant_regex, email_body, re.IGNORECASE)
            if match:
                extracted['merchant'] = match.group('merchant') if 'merchant' in match.groupdict() else match.group(1)
                confidence_scores.append(0.6)
        
        # Extract reference
        if self.reference_regex and email_body:
            match = re.search(self.reference_regex, email_body, re.IGNORECASE)
            if match:
                extracted['reference'] = match.group('reference') if 'reference' in match.groupdict() else match.group(1)
                confidence_scores.append(0.5)
        
        # Calculate overall confidence
        overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        return {
            'extracted_data': extracted,
            'confidence_score': overall_confidence,
            'template_id': self.id,
            'template_name': self.template_name
        } 