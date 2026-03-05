
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class KotakDataExtractionService:
    def __init__(self):
        # Kotak-specific patterns
        self.kotak_patterns = {
            'date': [
                r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b',
                r'\b(\d{1,2}\.\d{1,2}\.\d{4})\b'
            ],
            'amount': [
                r'\b(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\b',
                r'\b(\d+\.\d{2})\b'
            ],
            'account': [
                r'A/c\s*[Nn]o\.?\s*:?\s*(\d{9,18})',
                r'Account\s*:?\s*(\d{9,18})'
            ]
        }

        self.kotak_keywords = {
            'salary': ['salary', 'sal credit', 'payroll'],
            'transfer': ['neft', 'rtgs', 'imps', 'upi', 'transfer'],
            'atm': ['atm', 'cash withdrawal', 'pos'],
            'interest': ['interest', 'int credit'],
            'charges': ['charges', 'service charge', 'fee'],
        }

    def extract_financial_data(self, text):
        try:
            logger.info("Starting Kotak extraction...")

            if not self._is_kotak_statement(text):
                logger.info("Not a Kotak statement, using generic extraction")
                return self._generic_extraction(text)

            logger.info("Confirmed Kotak statement")

            account_info = self._extract_account_info(text)
            transactions = self._extract_kotak_transactions(text)

            if not transactions:
                return {
                    'error': 'No transactions found in Kotak statement',
                    'debug_info': {
                        'text_length': len(text),
                        'kotak_keywords': self._debug_kotak_keywords(text),
                        'text_preview': text[:300]
                    }
                }

            summary = self._generate_summary(transactions)

            return {
                'transactions': transactions,
                'account_info': account_info,
                'summary': summary,
                'bank': 'Kotak Mahindra Bank'
            }

        except Exception as e:
            logger.error(f"Kotak extraction failed: {e}")
            return {
                'error': f'Failed to extract Kotak data: {str(e)}',
                'debug_info': {'text_preview': text[:200] if text else ''}
            }

    def _is_kotak_statement(self, text):
        identifiers = ['kotak mahindra', 'kotak bank', 'kotak']
        return any(id in text.lower() for id in identifiers)

    def _extract_account_info(self, text):
        account_info = {}

        for pattern in self.kotak_patterns['account']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                account_info['account_number'] = match.group(1)
                break

        name_patterns = [r'Customer\s*Name\s*:?\s*([A-Z\s]+)']
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if len(name) > 2:
                    account_info['holder_name'] = name
                    break

        return account_info

    def _extract_kotak_transactions(self, text):
        transactions = []

        lines = text.split('\n')

        # Try tabular extraction
        transactions.extend(self._extract_tabular_transactions(lines))

        if not transactions:
            transactions.extend(self._extract_pattern_transactions(text))

        return [t for t in transactions if self._validate_transaction(t)]

    def _extract_tabular_transactions(self, lines):
        transactions = []
        in_transaction_section = False

        for line in lines:
            line = line.strip()
            if not line or len(line) < 15:
                continue

            line_lower = line.lower()

            # Check for transaction table start
            if any(keyword in line_lower for keyword in ['date', 'description', 'debit', 'credit']):
                in_transaction_section = True
                continue

            if in_transaction_section:
                transaction = self._parse_transaction_line(line)
                if transaction:
                    transactions.append(transaction)

        return transactions

    def _parse_transaction_line(self, line):
        try:
            # Find date
            date_match = None
            for pattern in self.kotak_patterns['date']:
                date_match = re.search(pattern, line)
                if date_match:
                    break

            if not date_match:
                return None

            date_str = date_match.group(1)
            remaining = line[date_match.end():].strip()

            # Find amounts
            amounts = []
            for pattern in self.kotak_patterns['amount']:
                amounts.extend(re.findall(pattern, remaining))

            if not amounts:
                return None

            amounts = [float(amt.replace(',', '')) for amt in amounts 
                      if amt.replace(',', '').replace('.', '').isdigit()]

            if not amounts:
                return None

            # Get description (text before amounts)
            description = remaining
            for amt_str in [str(amt) for amt in amounts]:
                description = description.replace(amt_str.replace('.0', ''), '')
                description = description.replace(amt_str, '')

            description = re.sub(r'[,\s]+', ' ', description).strip()

            # Determine transaction type and amount
            if len(amounts) >= 2:
                amount = amounts[0]
                balance = amounts[-1]
            else:
                amount = amounts[0]
                balance = 0

            # Determine type based on description or position
            txn_type = 'credit' if any(word in description.lower() 
                                     for word in ['credit', 'deposit', 'salary', 'interest']) else 'debit'

            category = self._classify_transaction(description)

            return {
                'date': self._standardize_date(date_str),
                'description': description,
                'amount': amount,
                'type': txn_type,
                'category': category,
                'balance': balance
            }

        except Exception as e:
            logger.debug(f"Failed to parse line: {e}")
            return None

    def _extract_pattern_transactions(self, text):
        transactions = []

        # Pattern for date + description + amount
        pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})([^\d]*?)(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'

        matches = re.finditer(pattern, text, re.MULTILINE)

        for match in matches:
            try:
                date_str = match.group(1)
                description = match.group(2).strip()
                amount_str = match.group(3).replace(',', '')

                if len(description) > 5:
                    transactions.append({
                        'date': self._standardize_date(date_str),
                        'description': description,
                        'amount': float(amount_str),
                        'type': 'debit',
                        'category': self._classify_transaction(description)
                    })
            except:
                continue

        return transactions

    def _classify_transaction(self, description):
        desc_lower = description.lower()

        for category, keywords in self.kotak_keywords.items():
            if any(keyword in desc_lower for keyword in keywords):
                return category

        return 'unknown'

    def _standardize_date(self, date_str):
        formats = ['%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y']

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
            except:
                continue

        return date_str

    def _validate_transaction(self, transaction):
        if not transaction:
            return False

        required = ['date', 'description', 'amount']
        if not all(field in transaction for field in required):
            return False

        if transaction['amount'] <= 0:
            return False

        if len(transaction['description'].strip()) < 3:
            return False

        return True

    def _generate_summary(self, transactions):
        if not transactions:
            return {}

        total_credits = sum(t['amount'] for t in transactions if t.get('type') == 'credit')
        total_debits = sum(t['amount'] for t in transactions if t.get('type') == 'debit')

        salary_income = sum(t['amount'] for t in transactions 
                           if t.get('category') == 'salary')

        return {
            'total_transactions': len(transactions),
            'total_credits': total_credits,
            'total_debits': total_debits,
            'salary_income': salary_income,
            'other_income': total_credits - salary_income
        }

    def _generic_extraction(self, text):
        transactions = []
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if len(line) < 15:
                continue

            date_match = re.search(r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b', line)
            if not date_match:
                continue

            amounts = re.findall(r'\b(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\b', line)
            if not amounts:
                continue

            amount = float(amounts[-1].replace(',', ''))
            description = re.sub(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', '', line)
            description = re.sub(r'\d{1,3}(?:,\d{3})*(?:\.\d{2})?', '', description)
            description = re.sub(r'\s+', ' ', description).strip()

            if len(description) > 3:
                transactions.append({
                    'date': self._standardize_date(date_match.group(1)),
                    'description': description,
                    'amount': amount,
                    'type': 'debit',
                    'category': 'unknown'
                })

        return {
            'transactions': transactions,
            'account_info': {},
            'summary': self._generate_summary(transactions),
            'extraction_method': 'generic'
        }

    def _debug_kotak_keywords(self, text):
        found = []
        keywords = ['kotak', 'account statement', 'transaction', 'debit', 'credit', 'balance']

        for keyword in keywords:
            if keyword in text.lower():
                found.append(keyword)

        return found

class EnhancedDataExtractionService:
    def __init__(self):
        self.kotak_service = KotakDataExtractionService()

    def extract_financial_data(self, text):
        return self.kotak_service.extract_financial_data(text)

    def classify_transactions(self, financial_data):
        return financial_data
