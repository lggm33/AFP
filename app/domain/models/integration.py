from datetime import datetime
from dataclasses import dataclass
from typing import Optional

@dataclass
class Integration:
    id: Optional[int] = None
    user_id: Optional[int] = None
    provider: str = "gmail"  # Preparado para futuras extensiones (outlook, etc.)
    email_account: str = ""
    is_active: bool = True
    access_token: str = ""
    refresh_token: str = ""
    last_sync: Optional[datetime] = None
    sync_frequency_minutes: int = 5
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None 