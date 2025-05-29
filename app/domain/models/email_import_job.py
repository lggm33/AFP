from datetime import datetime
from dataclasses import dataclass
from typing import Optional

@dataclass
class EmailImportJob:
    id: Optional[int] = None
    integration_id: Optional[int] = None
    status: str = "pending"  # pending, running, completed, failed
    emails_processed: int = 0
    emails_found: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: str = ""
    last_message_id: str = ""  # Para sincronización incremental
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None 