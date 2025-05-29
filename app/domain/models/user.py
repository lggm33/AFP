from datetime import datetime
from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    id: Optional[int] = None
    email: str = ""
    full_name: str = ""
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None 