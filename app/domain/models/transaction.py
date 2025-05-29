from datetime import datetime
from dataclasses import dataclass
from typing import Optional

@dataclass
class Transaction:
    id: Optional[int] = None
    description: str = ""
    amount: float = 0.0
    date: Optional[datetime] = None
    source: str = ""
    email_id: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    from_bank: str = ""
    to_bank: str = ""
    # Nuevos campos para trazabilidad
    email_parsing_job_id: Optional[int] = None
    confidence_score: float = 0.0  # Confianza del parsing (0.0 - 1.0)
    verification_status: str = "auto"  # auto, manual_verified, disputed
