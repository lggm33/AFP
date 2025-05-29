from datetime import datetime
from dataclasses import dataclass
from typing import Optional

@dataclass
class EmailParsingJob:
    id: Optional[int] = None
    email_import_job_id: Optional[int] = None
    bank_id: Optional[int] = None
    email_message_id: str = ""
    email_subject: str = ""
    email_from: str = ""
    email_body: str = ""  # Contenido raw para debugging
    parsing_status: str = "pending"  # pending, success, failed, manual_review
    confidence_score: float = 0.0  # 0.0 - 1.0
    parsing_attempts: int = 0
    error_message: str = ""
    processed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None 