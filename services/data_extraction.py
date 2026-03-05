import re
from datetime import datetime
import logging
from typing import List, Dict, Optional, Tuple
import pdfplumber
import hashlib

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class DataExtractionService:
    def __init__(self):
        self.patterns = {
            # Strict Indian date formats
            'date': r'\b(0?[1-9]|[12][0-9]|3[01])[\-/](0?[1-9]|1[0-2])[\-/](\d{2}|\d{4})\b',
            # Amounts with Indian separators and optional decimals
            'amount': r'\b(?:Rs\.?\s*)?(\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)\b',
            # Credit / Debit markers
            'credit_marker': r'\b(CR|CREDIT)\b',
            'debit_marker': r'\b(DR|DEBIT)\b'
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

    # ----------------- TEXT EXTRACTION -----------------
    def _extract_transactions(self, text: str) -> List[Dict]:
        transactions: List[Dict] = []
        lines = [l.strip() for l in (text or '').split('\n') if l.strip()]

        date_pattern = re.compile(self.patterns['date'], re.IGNORECASE)
        current_block: List[str] = []

        def flush_block(block: List[str]):
            if not block:
                return
            row_text = ' '.join(block)
            self._extract_transactions_from_line(row_text, transactions)

        for line in lines:
            if date_pattern.search(line):
                flush_block(current_block)
                current_block = [line]
            else:
                if current_block:
                    current_block.append(line)
        flush_block(current_block)
        return transactions

    def _extract_transactions_from_line(self, line: str, out: List[Dict]):
        date_match = re.search(self.patterns['date'], line)
        if not date_match:
            return
        date_str = date_match.group(0)

        amounts = re.findall(self.patterns['amount'], line)
        if not amounts:
            return

        lower = line.lower()
        if re.search(self.patterns['credit_marker'], line, flags=re.IGNORECASE) or ' cr ' in f" {lower} ":
            ttype = 'credit'
        elif re.search(self.patterns['debit_marker'], line, flags=re.IGNORECASE) or ' dr ' in f" {lower} ":
            ttype = 'debit'
        else:
            ttype = 'debit'

        raw_amount = amounts[-1]
        try:
            amount_val = float(raw_amount.replace(',', ''))
        except Exception:
            return

        out.append({
            'date': date_str,
            'description': line.strip(),
            'amount': abs(amount_val),
            'type': ttype
        })

    # ----------------- PDF TABLE EXTRACTION -----------------
    def _extract_transactions_from_pdf_tables(self, pdf_path: str) -> List[Dict]:
        transactions: List[Dict] = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                try:
                    tables = page.extract_tables() or []
                except Exception:
                    tables = []

                for table in tables:
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

        for idx, row in enumerate(norm[:10]):
            joined = ' '.join(row).lower()
            if any(k in joined for k in ['date', 'transaction', 'description', 'debit', 'credit', 'withdrawal', 'deposit', 'amount', 'balance']):
                colmap: Dict[str, int] = {}
                for i, cell in enumerate(row):
                    c = (cell or '').strip().lower()
                    if 'date' in c:
                        colmap['date'] = i
                    if 'description' in c or 'particular' in c or 'narration' in c or 'transaction' in c:
                        colmap['description'] = i
                    if 'debit' in c or 'withdrawal' in c or 'wdl' in c:
                        colmap['debit'] = i
                    if 'credit' in c or 'deposit' in c:
                        colmap['credit'] = i
                    if 'amount' in c and 'balance' not in c and 'credit' not in c and 'debit' not in c:
                        colmap['amount'] = i
                if 'date' in colmap and ('amount' in colmap or 'debit' in colmap or 'credit' in colmap):
                    best_header_idx = idx
                    best_cols = colmap
                    break
        return best_header_idx, best_cols

    def _parse_table_row(self, row: List[Optional[str]], cols: Dict[str, int]) -> Optional[Dict]:
        def cell(index_name: str) -> str:
            idx = cols.get(index_name, -1)
            return (row[idx] or '').strip() if 0 <= idx < len(row) else ''

        date_cell = cell('date')
        if not re.search(self.patterns['date'], date_cell):
            return None

        description = cell('description') or ''
        debit_str = cell('debit')
        credit_str = cell('credit')
        amount_str = cell('amount')

        amount_val = None
        ttype = 'debit'
        for s, t in [(debit_str, 'debit'), (credit_str, 'credit'), (amount_str, 'debit')]:
            if not s:
                continue
            m = re.search(self.patterns['amount'], s)
            if m:
                amount_val = float(m.group(1).replace(',', ''))
                ttype = t
                break
        if amount_val is None:
            return None

        return {
            'date': date_cell.strip(),
            'description': description.strip() or (amount_str or '').strip(),
            'amount': abs(amount_val),
            'type': ttype
        }

    # ----------------- IMPROVED MERGE FUNCTION -----------------
    def _merge_transactions(self, a: List[Dict], b: List[Dict]) -> List[Dict]:
        """Merge transactions with strict duplicate prevention."""
        def normalize_date(date_str: str) -> str:
            date_str = date_str.strip()
            date_str = re.sub(r'[^\d/.-]', '', date_str)
            for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    return date_obj.strftime("%Y-%m-%d")
                except Exception:
                    continue
            return date_str

        def normalize_text(text: str) -> str:
            text = text.lower()
            text = re.sub(r'[^a-z0-9\s]', '', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text

        seen_hashes = set()
        merged = []

        for src in (a, b):
            for t in src:
                date = normalize_date(t.get('date', ''))
                desc = normalize_text(t.get('description', ''))
                amt = round(float(t.get('amount', 0.0)), 2)
                ttype = t.get('type', 'debit')

                hash_key = hashlib.md5(f"{date}-{amt}-{ttype}-{desc[:60]}".encode()).hexdigest()
                if hash_key in seen_hashes:
                    continue

                seen_hashes.add(hash_key)
                t['date'] = date
                t['description'] = desc
                t['amount'] = amt
                t['type'] = ttype
                merged.append(t)

        logger.info(f"Merged transactions: {len(a) + len(b)} → Unique: {len(merged)}")
        return merged

    # ----------------- ACCOUNT INFO EXTRACTION -----------------
    def _extract_account_info(self, text: str) -> Dict:
        account_info = {}
        acc_match = re.search(r'(A/c|Account)\s*[Nn]o\.?\s*:?:?\s*(\d{6,18})', text)
        if acc_match:
            account_info['account_number'] = acc_match.group(2)
        return account_info

    # ----------------- SUMMARY GENERATION -----------------
    def _generate_summary(self, transactions: List[Dict]) -> Dict:
        total_credits = sum(t['amount'] for t in transactions if t['type'] == 'credit')
        total_debits = sum(t['amount'] for t in transactions if t['type'] == 'debit')
        return {
            'total_transactions': len(transactions),
            'total_credits': total_credits,
            'total_debits': total_debits,
        }

    # ----------------- TRANSACTION CLASSIFICATION -----------------
    def classify_transactions(self, transactions: List[Dict]) -> List[Dict]:
        categories = {
            'salary': ['salary', 'payroll', 'ctc', 'incentive'],
            'shopping': ['amazon', 'flipkart', 'paytm', 'myntra', 'grocery', 'shopping'],
            'utilities': ['electricity', 'water', 'gas', 'bill', 'utility'],
            'food': ['restaurant', 'cafe', 'dining', 'food', 'starbucks', 'dominos'],
            'rent': ['rent', 'landlord', 'apartment'],
            'transfer': ['upi', 'neft', 'imps', 'transfer', 'payment']
        }

        classified = []
        for t in transactions:
            desc_lower = t['description'].lower()
            t['category'] = 'others'
            for cat, keywords in categories.items():
                if any(k in desc_lower for k in keywords):
                    t['category'] = cat
                    break
            classified.append(t)
        return classified
