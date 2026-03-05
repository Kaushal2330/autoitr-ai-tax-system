import re
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import pdfplumber

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class DataExtractionService:
    def __init__(self):
        self.patterns = {
            # Enhanced date patterns - DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY, DD MMM YYYY, more formats
            'date_numeric': r'\b(0?[1-9]|[12][0-9]|3[01])[\-\.\/](0?[1-9]|1[0-2])[\-\.\/](\d{2}|\d{4})\b',
            'date_words': r'\b(0?[1-9]|[12][0-9]|3[01])\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{2}|\d{4})\b',
            'date_reverse': r'\b(\d{4})[\-\.\/](0?[1-9]|1[0-2])[\-\.\/](0?[1-9]|[12][0-9]|3[01])\b',
            'date_ddmmyy': r'\b(\d{1,2})[\-\.\/](\d{1,2})[\-\.\/](\d{2})\b',  # DD/MM/YY
            'date_mmddyy': r'\b(\d{1,2})[\-\.\/](\d{1,2})[\-\.\/](\d{2})\b',  # MM/DD/YY (ambiguous, but included)

            # Enhanced amount patterns - Indian format, international format, with currency symbols, more variations
            'amount_indian': r'\b(?:Rs\.?\s*|₹\s*|INR\s*)?(\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})?)\b',
            'amount_international': r'\b(?:Rs\.?\s*|₹\s*|INR\s*)?(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\b',
            'amount_simple': r'\b(?:Rs\.?\s*|₹\s*|INR\s*)?(\d+(?:\.\d{1,2})?)\b',
            'amount_negative': r'\b(?:Rs\.?\s*|₹\s*|INR\s*)?\-(\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)\b',
            'amount_with_space': r'\b(?:Rs\.?\s*|₹\s*|INR\s*)?\s*(\d{1,3}(?:\s\d{2,3})*(?:\.\d{1,2})?)\b',  # Space separated like 1 23 456.78

            # Enhanced transaction type markers - more keywords
            'credit_marker': r'\b(CR|CREDIT|DEPOSIT|CREDITED|RECEIVED|CREDIT\s+TRANSFER|UPI\s+CREDIT|NEFT\s+CREDIT|RTGS\s+CREDIT|SALARY|INTEREST|DIVIDEND|REFUND|REBATE|BONUS|CASHBACK|INCENTIVE|COMMISSION|ROYALTY|RENTAL|INCOME)\b',
            'debit_marker': r'\b(DR|DEBIT|WITHDRAWAL|WITHDRAWN|PAID|PAYMENT|DEBIT\s+TRANSFER|UPI\s+DEBIT|NEFT\s+DEBIT|RTGS\s+DEBIT|ATM|POS|CHEQUE|CHARGE|FEE|PURCHASE|EXPENSE|BILL|EMI|LOAN|INSURANCE|SUBSCRIPTION|TAX|GST|VAT|FINE|PENALTY)\b',

            # Account number patterns - more variations
            'account_number': r'\b(?:A\/c\s*No\.?\s*:?\s*|Account\s*No\.?\s*:?\s*|A\/C\s*:?\s*|Acc\s*No\.?\s*:?\s*|Account\s*Number\s*:?\s*)(\d{6,18})\b',

            # Balance patterns - more variations
            'balance': r'\b(?:Balance\s*:?\s*|Bal\s*:?\s*|Closing\s*Balance\s*:?\s*|Opening\s*Balance\s*:?\s*|Current\s*Balance\s*:?\s*)(?:Rs\.?\s*|₹\s*|INR\s*)?(\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})?)\b',

            # UPI ID patterns
            'upi_id': r'\b([a-zA-Z0-9\.\-_]+@[a-zA-Z0-9\.\-_]+)\b',

            # Transaction reference patterns
            'txn_ref': r'\b(?:Txn\s*ID|Transaction\s*ID|Ref\s*No|Reference\s*No|UTR|UTR\s*No)\s*:?\s*([A-Z0-9]{8,20})\b'
        }
        
        # Bank-specific patterns - expanded with more banks and better patterns
        self.bank_patterns = {
            'sbi': {
                'date': r'\b(\d{1,2}[\-\.\/]\d{1,2}[\-\.\/]\d{2,4})\b',
                'amount': r'\b(\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?)\b',
                'description': r'(UPI|NEFT|RTGS|ATM|POS|CHEQUE|TRANSFER|SALARY|INTEREST|IMPS|CASH|ECS|BILLPAY)',
                'credit_keywords': ['SALARY', 'INTEREST', 'DIVIDEND', 'REFUND', 'CREDIT'],
                'debit_keywords': ['ATM', 'POS', 'CHEQUE', 'TRANSFER', 'BILLPAY']
            },
            'hdfc': {
                'date': r'\b(\d{1,2}[\-\.\/]\d{1,2}[\-\.\/]\d{2,4})\b',
                'amount': r'\b(?:Rs\.?\s*)?(\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?)\b',
                'description': r'(UPI|NEFT|RTGS|ATM|POS|CHEQUE|TRANSFER|SALARY|INTEREST|IMPS|CASH|ECS|BILLPAY|SWIFT)',
                'credit_keywords': ['SALARY', 'INTEREST', 'DIVIDEND', 'REFUND', 'CREDIT', 'DEPOSIT'],
                'debit_keywords': ['ATM', 'POS', 'CHEQUE', 'TRANSFER', 'BILLPAY', 'WITHDRAWAL']
            },
            'icici': {
                'date': r'\b(\d{1,2}[\-\.\/]\d{1,2}[\-\.\/]\d{2,4})\b',
                'amount': r'\b(?:Rs\.?\s*)?(\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?)\b',
                'description': r'(UPI|NEFT|RTGS|ATM|POS|CHEQUE|TRANSFER|SALARY|INTEREST|IMPS|MOBILE|CASH|ECS|BILLPAY|SWIFT)',
                'credit_keywords': ['SALARY', 'INTEREST', 'DIVIDEND', 'REFUND', 'CREDIT', 'DEPOSIT'],
                'debit_keywords': ['ATM', 'POS', 'CHEQUE', 'TRANSFER', 'BILLPAY', 'WITHDRAWAL', 'PAYMENT']
            },
            'axis': {
                'date': r'\b(\d{1,2}[\-\.\/]\d{1,2}[\-\.\/]\d{2,4})\b',
                'amount': r'\b(?:Rs\.?\s*)?(\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?)\b',
                'description': r'(UPI|NEFT|RTGS|ATM|POS|CHEQUE|TRANSFER|SALARY|INTEREST|IMPS|CASH|ECS|BILLPAY)',
                'credit_keywords': ['SALARY', 'INTEREST', 'DIVIDEND', 'REFUND', 'CREDIT'],
                'debit_keywords': ['ATM', 'POS', 'CHEQUE', 'TRANSFER', 'BILLPAY', 'WITHDRAWAL']
            },
            'kotak': {
                'date': r'\b(\d{1,2}[\-\.\/]\d{1,2}[\-\.\/]\d{2,4})\b',
                'amount': r'\b(?:Rs\.?\s*)?(\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?)\b',
                'description': r'(UPI|NEFT|RTGS|ATM|POS|CHEQUE|TRANSFER|SALARY|INTEREST|IMPS|CASH|ECS|BILLPAY)',
                'credit_keywords': ['SALARY', 'INTEREST', 'DIVIDEND', 'REFUND', 'CREDIT'],
                'debit_keywords': ['ATM', 'POS', 'CHEQUE', 'TRANSFER', 'BILLPAY', 'WITHDRAWAL']
            },
            'pnb': {
                'date': r'\b(\d{1,2}[\-\.\/]\d{1,2}[\-\.\/]\d{2,4})\b',
                'amount': r'\b(?:Rs\.?\s*)?(\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?)\b',
                'description': r'(UPI|NEFT|RTGS|ATM|POS|CHEQUE|TRANSFER|SALARY|INTEREST|IMPS|CASH|ECS)',
                'credit_keywords': ['SALARY', 'INTEREST', 'DIVIDEND', 'REFUND', 'CREDIT'],
                'debit_keywords': ['ATM', 'POS', 'CHEQUE', 'TRANSFER', 'WITHDRAWAL']
            }
        }

    def extract_financial_data(self, text: str, source_path: Optional[str] = None) -> Dict:
        try:
            transactions_text = self._extract_transactions(text)
            transactions_tables: List[Dict] = []

            if source_path and source_path.lower().endswith('.pdf'):
                try:
                    transactions_tables = self._extract_transactions_from_pdf_tables(source_path)
                except Exception as e:
                    logger.warning(f"PDF table extraction failed: {e}")

            transactions = self._merge_transactions(transactions_text, transactions_tables)
            account_info = self._extract_account_info(text)
            summary = self._generate_summary(transactions)
            classified = self.classify_transactions(transactions)

            return {
                'transactions': transactions,
                'account_info': account_info,
                'summary': summary,
                'classified_transactions': classified,
                'debug': {
                    'text_rows_detected': len(transactions_text),
                    'table_rows_detected': len(transactions_tables)
                }
            }
        except Exception as e:
            logger.error(f"Data extraction failed: {e}")
            return {}

    def _extract_transactions(self, text: str) -> List[Dict]:
        transactions: List[Dict] = []
        lines = [l for l in (text or '').split('\n')]

        # Detect bank type for better parsing
        bank_type = self._detect_bank_type(text)
        logger.info(f"Detected bank type: {bank_type}")

        # Group multiline rows by detecting date-start lines
        current_block: List[str] = []
        
        # Try multiple date patterns
        date_patterns = [
            re.compile(self.patterns['date_numeric'], re.IGNORECASE),
            re.compile(self.patterns['date_words'], re.IGNORECASE),
            re.compile(self.patterns['date_reverse'], re.IGNORECASE)
        ]

        def flush_block(block: List[str]):
            if not block:
                return
            row_text = ' '.join([b.strip() for b in block if b.strip()])
            self._extract_transactions_from_line(row_text, transactions, bank_type)

        for raw in lines:
            line = raw.strip()
            if not line or len(line) < 5:
                continue
                
            # Check if line starts with a date
            is_date_line = any(pattern.search(line) for pattern in date_patterns)
            
            if is_date_line:
                flush_block(current_block)
                current_block = [line]
            else:
                if current_block:
                    current_block.append(line)
                else:
                    # Try to find transactions even without clear date markers
                    self._extract_transactions_from_line(line, transactions, bank_type)
                    
        flush_block(current_block)

        return self._validate_and_clean_transactions(transactions)

    def _extract_transactions_from_line(self, line: str, out: List[Dict], bank_type: str = 'generic'):
        # Try multiple date patterns including new ones
        date_match = None
        for pattern_name in ['date_numeric', 'date_words', 'date_reverse', 'date_ddmmyy']:
            date_match = re.search(self.patterns[pattern_name], line, re.IGNORECASE)
            if date_match:
                break

        if not date_match:
            return

        date_str = date_match.group(0)

        # Try multiple amount patterns including new space-separated
        amounts = []
        for pattern_name in ['amount_indian', 'amount_international', 'amount_simple', 'amount_with_space']:
            amounts = re.findall(self.patterns[pattern_name], line)
            if amounts:
                break

        # Check for negative amounts
        if not amounts:
            negative_amounts = re.findall(self.patterns['amount_negative'], line)
            if negative_amounts:
                amounts = negative_amounts

        if not amounts:
            return

        # Enhanced transaction type detection with bank-specific keywords
        lower = line.lower()
        ttype = 'debit'  # Default to debit

        # Bank-specific detection
        bank_config = self.bank_patterns.get(bank_type, {})
        credit_keywords = bank_config.get('credit_keywords', [])
        debit_keywords = bank_config.get('debit_keywords', [])

        # Credit detection - enhanced
        credit_indicators = [
            re.search(self.patterns['credit_marker'], line, flags=re.IGNORECASE),
            any(marker in lower for marker in [' cr ', 'credit', 'deposit', 'received', 'salary', 'interest', 'dividend', 'refund', 'bonus']),
            any(keyword in lower for keyword in credit_keywords)
        ]
        if any(credit_indicators):
            ttype = 'credit'

        # Debit detection - enhanced
        debit_indicators = [
            re.search(self.patterns['debit_marker'], line, flags=re.IGNORECASE),
            any(marker in lower for marker in [' dr ', 'debit', 'withdrawal', 'paid', 'payment', 'atm', 'pos', 'cheque', 'charge', 'fee', 'purchase']),
            any(keyword in lower for keyword in debit_keywords)
        ]
        if any(debit_indicators):
            ttype = 'debit'

        # Heuristic: negative amounts are usually debits
        if re.search(self.patterns['amount_negative'], line):
            ttype = 'debit'

        # Extract amount (prefer the last/largest amount as transaction amount)
        raw_amount = amounts[-1]
        try:
            # Handle space-separated amounts
            amount_val = float(raw_amount.replace(',', '').replace(' ', ''))
        except Exception:
            return

        # Enhanced description extraction
        description = self._extract_description(line, bank_type)

        # Extract additional metadata
        upi_id = re.search(self.patterns['upi_id'], line)
        txn_ref = re.search(self.patterns['txn_ref'], line)

        transaction = {
            'date': self._normalize_date(date_str),
            'description': description,
            'amount': abs(amount_val),
            'type': ttype,
            'raw_line': line.strip(),
            'upi_id': upi_id.group(1) if upi_id else None,
            'txn_ref': txn_ref.group(1) if txn_ref else None
        }

        out.append(transaction)

    def _extract_transactions_from_pdf_tables(self, pdf_path: str) -> List[Dict]:
        transactions: List[Dict] = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                try:
                    tables = page.extract_tables()
                except Exception:
                    tables = []
                for table in tables or []:
                    if not table or len(table) < 2:
                        continue
                    header_idx, cols = self._infer_table_layout(table)
                    if header_idx is None or not cols:
                        continue
                    for row in table[header_idx + 1:]:
                        if not any(row):
                            continue
                        tx = self._parse_table_row(row, cols)
                        if tx:
                            transactions.append(tx)
        return transactions

    def _infer_table_layout(self, table: List[List[Optional[str]]]) -> Tuple[Optional[int], Dict[str, int]]:
        norm = [[(c or '').strip() for c in row] for row in table]
        best_header_idx = None
        best_cols: Dict[str, int] = {}
        best_score = 0
        
        # Enhanced header detection patterns
        header_keywords = {
            'date': ['date', 'transaction date', 'tran date', 'dt', 'dte'],
            'description': ['description', 'particular', 'narration', 'transaction', 'details', 'remark', 'narrative'],
            'debit': ['debit', 'withdrawal', 'wdl', 'debit amount', 'paid', 'payment'],
            'credit': ['credit', 'deposit', 'credit amount', 'received', 'dep'],
            'amount': ['amount', 'transaction amount', 'tran amount', 'value'],
            'balance': ['balance', 'closing balance', 'running balance', 'bal']
        }
        
        for idx, row in enumerate(norm[:5]):
            joined = ' '.join(row).lower()
            colmap: Dict[str, int] = {}
            score = 0
            
            # Check if this row contains header keywords
            for col_type, keywords in header_keywords.items():
                for i, cell in enumerate(row):
                    cell_lower = (cell or '').strip().lower()
                    if any(keyword in cell_lower for keyword in keywords):
                        colmap[col_type] = i
                        score += 1
                        break
            
            # Bonus points for having date and amount columns
            if 'date' in colmap:
                score += 2
            if 'amount' in colmap or ('debit' in colmap and 'credit' in colmap):
                score += 2
            
            # Prefer this layout if it has better score
            if score > best_score and len(colmap) >= 2:
                best_score = score
                best_header_idx = idx
                best_cols = colmap
        
        return best_header_idx, best_cols

    def _parse_table_row(self, row: List[Optional[str]], cols: Dict[str, int]) -> Optional[Dict]:
        def cell(index_name: str) -> str:
            idx = cols.get(index_name, -1)
            return (row[idx] or '').strip() if 0 <= idx < len(row) else ''

        date_cell = cell('date')

        # Try multiple date patterns for table rows including new ones
        date_match = None
        for pattern_name in ['date_numeric', 'date_words', 'date_reverse', 'date_ddmmyy']:
            date_match = re.search(self.patterns[pattern_name], date_cell, re.IGNORECASE)
            if date_match:
                break

        if not date_match:
            return None

        description = cell('description') or ''
        debit_str = cell('debit')
        credit_str = cell('credit')
        amount_str = cell('amount')

        # Enhanced amount extraction for table rows with space handling
        amount_val = None
        ttype = 'debit'

        # Check debit column first
        if debit_str:
            for pattern_name in ['amount_indian', 'amount_international', 'amount_simple', 'amount_with_space']:
                m = re.search(self.patterns[pattern_name], debit_str)
                if m:
                    amount_val = float(m.group(1).replace(',', '').replace(' ', ''))
                    ttype = 'debit'
                    break

        # Check credit column
        if not amount_val and credit_str:
            for pattern_name in ['amount_indian', 'amount_international', 'amount_simple', 'amount_with_space']:
                m = re.search(self.patterns[pattern_name], credit_str)
                if m:
                    amount_val = float(m.group(1).replace(',', '').replace(' ', ''))
                    ttype = 'credit'
                    break

        # Check general amount column
        if not amount_val and amount_str:
            for pattern_name in ['amount_indian', 'amount_international', 'amount_simple', 'amount_with_space']:
                m = re.search(self.patterns[pattern_name], amount_str)
                if m:
                    amount_val = float(m.group(1).replace(',', '').replace(' ', ''))
                    # Try to determine type from context
                    if any(keyword in amount_str.lower() for keyword in ['cr', 'credit', 'deposit']):
                        ttype = 'credit'
                    elif any(keyword in amount_str.lower() for keyword in ['dr', 'debit', 'withdrawal']):
                        ttype = 'debit'
                    break

        if amount_val is None or amount_val <= 0:
            return None

        # Enhanced description extraction with UPI and ref extraction
        if not description:
            description = amount_str or 'Table Transaction'

        # Extract additional metadata for table rows
        upi_id = None
        txn_ref = None
        if description:
            upi_match = re.search(self.patterns['upi_id'], description)
            ref_match = re.search(self.patterns['txn_ref'], description)
            if upi_match:
                upi_id = upi_match.group(1)
            if ref_match:
                txn_ref = ref_match.group(1)

        return {
            'date': self._normalize_date(date_match.group(0)),
            'description': description.strip(),
            'amount': abs(amount_val),
            'type': ttype,
            'source': 'table',
            'upi_id': upi_id,
            'txn_ref': txn_ref
        }

    def _merge_transactions(self, a: List[Dict], b: List[Dict]) -> List[Dict]:
        seen = set()
        merged: List[Dict] = []
        for src in (a, b):
            for t in src:
                key = (t.get('date', ''), t.get('description', '')[:80], t.get('amount', 0.0))
                if key in seen:
                    continue
                seen.add(key)
                merged.append(t)
        return merged

    def _extract_account_info(self, text: str) -> Dict:
        account_info: Dict = {}

        # Enhanced account number extraction
        acc_patterns = [
            r'(?:A/c|Account)\s*[Nn]o\.?\s*:?\s*(\d{6,18})',
            r'[Aa]ccount\s*[Nn]umber\s*:?\s*(\d{6,18})',
            r'[Aa]/[Cc]\s*:?\s*(\d{6,18})',
            r'[Aa]cc\.?\s*[Nn]o\.?\s*:?\s*(\d{6,18})',
            r'Account\s*:?\s*(\d{6,18})'
        ]
        
        for pattern in acc_patterns:
            acc_match = re.search(pattern, text, re.IGNORECASE)
            if acc_match:
                account_info['account_number'] = acc_match.group(1)
                break

        # Extract account holder name
        name_patterns = [
            r'(?:Account\s*Holder|Name)\s*:?\s*([A-Za-z\s]{3,50})',
            r'Mr\.?\s+([A-Za-z\s]{3,30})',
            r'Mrs\.?\s+([A-Za-z\s]{3,30})',
            r'Ms\.?\s+([A-Za-z\s]{3,30})'
        ]
        
        for pattern in name_patterns:
            name_match = re.search(pattern, text, re.IGNORECASE)
            if name_match:
                account_info['holder_name'] = name_match.group(1).strip()
                break

        # Extract branch information
        branch_patterns = [
            r'Branch\s*:?\s*([A-Za-z\s]{3,50})',
            r'Branch\s*Code\s*:?\s*(\d{6})',
            r'IFSC\s*:?\s*([A-Z]{4}0[A-Z0-9]{6})'
        ]
        
        for pattern in branch_patterns:
            branch_match = re.search(pattern, text, re.IGNORECASE)
            if branch_match:
                account_info['branch'] = branch_match.group(1).strip()
                break

        return account_info

    def _generate_summary(self, transactions: List[Dict]) -> Dict:
        total_credits = sum(t['amount'] for t in transactions if t['type'] == 'credit')
        total_debits = sum(t['amount'] for t in transactions if t['type'] == 'debit')

        return {
            'total_transactions': len(transactions),
            'total_credits': total_credits,
            'total_debits': total_debits,
            'salary_income': total_credits * 0.8,
            'other_income': total_credits * 0.2
        }

    def classify_transactions(self, transactions: List[Dict]) -> List[Dict]:
        return transactions

    def _detect_bank_type(self, text: str) -> str:
        """Detect bank type from text content"""
        text_lower = text.lower()
        
        bank_indicators = {
            'sbi': ['state bank of india', 'sbi', 'sbi bank'],
            'hdfc': ['hdfc bank', 'hdfc'],
            'icici': ['icici bank', 'icici'],
            'axis': ['axis bank', 'axis'],
            'kotak': ['kotak mahindra', 'kotak bank', 'kotak'],
            'pnb': ['punjab national bank', 'pnb'],
            'bob': ['bank of baroda', 'bob'],
            'canara': ['canara bank', 'canara'],
            'union': ['union bank of india', 'union bank'],
            'indian': ['indian bank', 'indian']
        }
        
        for bank, indicators in bank_indicators.items():
            if any(indicator in text_lower for indicator in indicators):
                return bank
        
        return 'generic'

    def _extract_description(self, line: str, bank_type: str) -> str:
        """Extract clean transaction description"""
        # Remove dates, amounts, and common noise
        cleaned = line

        # Remove date patterns
        for pattern_name in ['date_numeric', 'date_words', 'date_reverse', 'date_ddmmyy']:
            cleaned = re.sub(self.patterns[pattern_name], '', cleaned, flags=re.IGNORECASE)

        # Remove amount patterns
        for pattern_name in ['amount_indian', 'amount_international', 'amount_simple', 'amount_negative', 'amount_with_space']:
            cleaned = re.sub(self.patterns[pattern_name], '', cleaned, flags=re.IGNORECASE)

        # Remove common noise words - expanded
        noise_words = ['cr', 'dr', 'credit', 'debit', 'rs', 'inr', '₹', 'rs.', 'inr.', 'transfer', 'payment', 'paid', 'received', 'withdrawal', 'deposit']
        for word in noise_words:
            cleaned = re.sub(rf'\b{word}\b', '', cleaned, flags=re.IGNORECASE)

        # Keep important identifiers like UPI IDs and transaction refs
        upi_match = re.search(self.patterns['upi_id'], line)
        txn_ref_match = re.search(self.patterns['txn_ref'], line)

        # Build description with important info
        description_parts = []

        # Add UPI ID if found
        if upi_match:
            description_parts.append(f"UPI-{upi_match.group(1)}")

        # Add transaction reference if found
        if txn_ref_match:
            description_parts.append(f"Ref-{txn_ref_match.group(1)}")

        # Clean the remaining text
        cleaned = re.sub(r'[^\w\s\-\.\/@]', ' ', cleaned)  # Keep @ for UPI
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # Add cleaned text if meaningful
        if cleaned and len(cleaned) > 3:
            description_parts.insert(0, cleaned)

        final_description = ' '.join(description_parts)

        return final_description if final_description else line.strip()

    def _normalize_date(self, date_str: str) -> str:
        """Normalize date to DD/MM/YYYY format with validation"""
        try:
            # Handle different date formats
            date_str = date_str.strip()

            # DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
            if re.match(r'\d{1,2}[\-\.\/]\d{1,2}[\-\.\/]\d{2,4}', date_str):
                parts = re.split(r'[\-\.\/]', date_str)
                day = int(parts[0])
                month = int(parts[1])
                year = int(parts[2])
                if len(str(year)) == 2:
                    year = 2000 + year
                # Validate date
                if 1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100:
                    return f"{day:02d}/{month:02d}/{year}"
                else:
                    raise ValueError("Invalid date components")

            # DD MMM YYYY format
            elif re.match(r'\d{1,2}\s+\w+\s+\d{2,4}', date_str):
                parts = date_str.split()
                day = int(parts[0])
                month_str = parts[1][:3].lower()
                year = int(parts[2])
                month_map = {
                    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
                    'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
                    'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                }
                month = month_map.get(month_str, 0)
                if len(str(year)) == 2:
                    year = 2000 + year
                # Validate date
                if month and 1 <= day <= 31 and 1900 <= year <= 2100:
                    return f"{day:02d}/{month:02d}/{year}"
                else:
                    raise ValueError("Invalid date components")

            # YYYY-MM-DD format
            elif re.match(r'\d{4}[\-\.\/]\d{1,2}[\-\.\/]\d{1,2}', date_str):
                parts = re.split(r'[\-\.\/]', date_str)
                year = int(parts[0])
                month = int(parts[1])
                day = int(parts[2])
                # Validate date
                if 1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100:
                    return f"{day:02d}/{month:02d}/{year}"
                else:
                    raise ValueError("Invalid date components")

            # DDMMYY format (compact)
            elif re.match(r'\d{6}', date_str) and len(date_str) == 6:
                day = int(date_str[:2])
                month = int(date_str[2:4])
                year = 2000 + int(date_str[4:])
                if 1 <= day <= 31 and 1 <= month <= 12:
                    return f"{day:02d}/{month:02d}/{year}"
                else:
                    raise ValueError("Invalid date components")

        except Exception as e:
            logger.warning(f"Date normalization failed for '{date_str}': {e}")

        return date_str

    def _validate_and_clean_transactions(self, transactions: List[Dict]) -> List[Dict]:
        """Validate and clean extracted transactions with enhanced checks"""
        cleaned_transactions = []

        for txn in transactions:
            try:
                # Basic validation
                if not txn.get('date') or not txn.get('amount'):
                    continue

                # Validate amount is reasonable (between 1 and 10 crore, allow smaller amounts for fees)
                amount = float(txn['amount'])
                if amount < 0.01 or amount > 100000000:  # 10 crore max
                    continue

                # Validate date format and range
                date_str = txn['date']
                if not re.match(r'\d{2}/\d{2}/\d{4}', date_str):
                    continue
                # Check if date is not in future (allow up to 1 day future for timezone issues)
                try:
                    txn_date = datetime.strptime(date_str, '%d/%m/%Y')
                    if txn_date > datetime.now() + datetime.timedelta(days=1):
                        continue
                    # Check if date is not too old (more than 10 years)
                    if txn_date < datetime.now() - datetime.timedelta(days=3650):
                        continue
                except ValueError:
                    continue

                # Clean description
                if not txn.get('description') or len(txn['description']) < 2:
                    txn['description'] = 'Transaction'

                # Validate transaction type
                if txn.get('type') not in ['credit', 'debit']:
                    txn['type'] = 'debit'  # Default to debit

                # Add confidence score based on data quality
                txn['confidence'] = self._calculate_confidence(txn)

                cleaned_transactions.append(txn)

            except Exception as e:
                logger.warning(f"Transaction validation failed: {e}")
                continue

        # Remove duplicates based on date, amount, and description similarity
        cleaned_transactions = self._remove_duplicates(cleaned_transactions)

        # Sort by date
        try:
            cleaned_transactions.sort(key=lambda x: datetime.strptime(x['date'], '%d/%m/%Y'))
        except Exception:
            cleaned_transactions.sort(key=lambda x: x['date'])

        logger.info(f"Validated and cleaned {len(cleaned_transactions)} transactions from {len(transactions)} raw transactions")
        return cleaned_transactions

    def _calculate_confidence(self, txn: Dict) -> float:
        """Calculate confidence score for a transaction with enhanced criteria"""
        score = 0.5  # Base score

        # Date quality and validation
        date_str = txn.get('date', '')
        if re.match(r'\d{2}/\d{2}/\d{4}', date_str):
            score += 0.15
            try:
                txn_date = datetime.strptime(date_str, '%d/%m/%Y')
                # Bonus for recent transactions
                days_old = (datetime.now() - txn_date).days
                if 0 <= days_old <= 365:
                    score += 0.05
            except ValueError:
                pass

        # Description quality
        desc = txn.get('description', '').lower()
        if len(desc) > 5:
            score += 0.1
        # Higher score for specific transaction types
        specific_keywords = ['upi', 'neft', 'rtgs', 'atm', 'pos', 'salary', 'interest', 'cheque', 'transfer', 'imps']
        if any(keyword in desc for keyword in specific_keywords):
            score += 0.15
        # Bonus for UPI ID or transaction reference
        if txn.get('upi_id') or txn.get('txn_ref'):
            score += 0.1

        # Amount reasonableness and patterns
        amount = float(txn.get('amount', 0))
        if 1 <= amount <= 5000000:  # Reasonable transaction range
            score += 0.1
            # Bonus for round amounts (often system-generated)
            if amount % 100 == 0:
                score += 0.05

        # Transaction type consistency
        txn_type = txn.get('type', '')
        desc_lower = desc
        if txn_type == 'credit' and any(word in desc_lower for word in ['salary', 'interest', 'refund', 'credit']):
            score += 0.05
        elif txn_type == 'debit' and any(word in desc_lower for word in ['atm', 'pos', 'payment', 'debit']):
            score += 0.05

        return min(1.0, score)

    def _remove_duplicates(self, transactions: List[Dict]) -> List[Dict]:
        """Remove duplicate transactions with enhanced logic"""
        seen = set()
        unique_transactions = []

        for txn in transactions:
            # Create multiple keys for better duplicate detection
            # Primary key: date, amount, description
            primary_key = (
                txn.get('date', ''),
                round(float(txn.get('amount', 0)), 2),
                txn.get('description', '')[:30].lower().strip()
            )

            # Secondary key: include UPI ID or transaction ref if available
            secondary_key = primary_key
            if txn.get('upi_id'):
                secondary_key = primary_key + (txn['upi_id'],)
            elif txn.get('txn_ref'):
                secondary_key = primary_key + (txn['txn_ref'],)

            # Use secondary key if available, otherwise primary
            key = secondary_key if len(secondary_key) > len(primary_key) else primary_key

            if key not in seen:
                seen.add(key)
                unique_transactions.append(txn)
            else:
                # Log duplicate for debugging
                logger.debug(f"Duplicate transaction removed: {primary_key}")

        return unique_transactions





