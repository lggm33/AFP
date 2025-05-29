from datetime import datetime
from dataclasses import dataclass
from typing import Optional

@dataclass
class Bank:
    id: Optional[int] = None
    name: str = ""
    domain: str = ""  # ejemplo: @bancolombia.com.co
    parsing_patterns: str = ""  # JSON con regex patterns
    is_active: bool = True
    confidence_threshold: float = 0.7
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None 