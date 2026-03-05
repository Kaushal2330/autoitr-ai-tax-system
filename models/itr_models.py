from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime

@dataclass
class Transaction:
    date: str
    description: str
    amount: float
    type: str
    category: str = 'unknown'

@dataclass
class ITRData:
    form_type: str = 'ITR1'
    assessment_year: str = '2025-26'
    financial_year: str = '2024-25'
    generated_date: str = ''

    def to_dict(self):
        return {
            'form_type': self.form_type,
            'assessment_year': self.assessment_year,
            'financial_year': self.financial_year,
            'generated_date': self.generated_date
        }
