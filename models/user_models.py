from dataclasses import dataclass, field
from typing import List
from datetime import datetime

@dataclass
class ValidationResult:
    overall_status: str = 'valid'
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    data_quality_score: int = 100
