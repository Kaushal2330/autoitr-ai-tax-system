import json
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ITRGenerator:
    def __init__(self):
        self.generated_dir = 'generated'
        os.makedirs(self.generated_dir, exist_ok=True)

    def generate_itr_preview(self, classified_data):
        try:
            summary = classified_data.get('summary', {})

            # Calculate tax
            tax_calc = self._calculate_tax(summary)

            return {
                'recommended_form': 'ITR1',
                'tax_calculation': tax_calc,
                'income_summary': {
                    'salary_income': summary.get('salary_income', 0),
                    'other_income': summary.get('other_income', 0),
                    'total_income': tax_calc['gross_total_income'],
                    'tax_liability': tax_calc['tax_liability']
                }
            }
        except Exception as e:
            logger.error(f"ITR preview failed: {e}")
            return None

    def _calculate_tax(self, summary):
        gross_income = summary.get('salary_income', 0) + summary.get('other_income', 0)
        standard_deduction = min(50000, summary.get('salary_income', 0))
        taxable_income = max(0, gross_income - standard_deduction)

        # Simple tax calculation
        tax_liability = 0
        if taxable_income > 250000:
            if taxable_income <= 500000:
                tax_liability = (taxable_income - 250000) * 0.05
            elif taxable_income <= 1000000:
                tax_liability = 12500 + (taxable_income - 500000) * 0.20
            else:
                tax_liability = 112500 + (taxable_income - 1000000) * 0.30

        return {
            'gross_total_income': gross_income,
            'standard_deduction': standard_deduction,
            'taxable_income': taxable_income,
            'tax_liability': tax_liability
        }

    def generate_itr_file(self, user_info, financial_data, format_type='json'):
        """Generate actual ITR file in specified format"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if format_type.lower() == 'json':
                # Generate JSON file
                json_data = self._create_itr_json(user_info, financial_data)
                filename = f"ITR_{timestamp}.json"
                file_path = os.path.join(self.generated_dir, filename)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=2, ensure_ascii=False)
                    
            elif format_type.lower() == 'xml':
                # Generate XML file
                xml_data = self._create_itr_xml(user_info, financial_data)
                filename = f"ITR_{timestamp}.xml"
                file_path = os.path.join(self.generated_dir, filename)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(xml_data)
            else:
                raise ValueError(f"Unsupported format: {format_type}")
            
            logger.info(f"Generated ITR file: {filename}")
            return file_path
            
        except Exception as e:
            logger.error(f"ITR file generation failed: {e}")
            raise

    def _create_itr_json(self, user_info, financial_data):
        """Create ITR data in JSON format"""
        summary = financial_data.get('summary', {})
        account_info = financial_data.get('account_info', {})
        transactions = financial_data.get('transactions', [])
        
        tax_calc = self._calculate_tax(summary)
        
        itr_data = {
            'itr_info': {
                'assessment_year': '2025-26',
                'form_type': 'ITR-1',
                'generated_date': datetime.now().isoformat(),
                'user_info': {
                    'name': user_info.get('name', ''),
                    'pan': user_info.get('pan', ''),
                    'address': user_info.get('address', ''),
                    'email': user_info.get('email', ''),
                    'phone': user_info.get('phone', '')
                },
                'account_info': account_info
            },
            'income_details': {
                'salary_income': summary.get('salary_income', 0),
                'other_income': summary.get('other_income', 0),
                'gross_total_income': tax_calc['gross_total_income'],
                'standard_deduction': tax_calc['standard_deduction'],
                'taxable_income': tax_calc['taxable_income']
            },
            'tax_calculation': tax_calc,
            'transactions': transactions[:50],  # Limit to first 50 transactions
            'summary': {
                'total_transactions': len(transactions),
                'total_credits': summary.get('total_credits', 0),
                'total_debits': summary.get('total_debits', 0)
            }
        }
        
        return itr_data

    def _create_itr_xml(self, user_info, financial_data):
        """Create ITR data in XML format"""
        summary = financial_data.get('summary', {})
        account_info = financial_data.get('account_info', {})
        transactions = financial_data.get('transactions', [])
        
        tax_calc = self._calculate_tax(summary)
        
        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<ITR>
    <Header>
        <AssessmentYear>2025-26</AssessmentYear>
        <FormType>ITR-1</FormType>
        <GeneratedDate>{datetime.now().isoformat()}</GeneratedDate>
    </Header>
    
    <UserInfo>
        <Name>{user_info.get('name', '')}</Name>
        <PAN>{user_info.get('pan', '')}</PAN>
        <Address>{user_info.get('address', '')}</Address>
        <Email>{user_info.get('email', '')}</Email>
        <Phone>{user_info.get('phone', '')}</Phone>
    </UserInfo>
    
    <AccountInfo>
        <AccountNumber>{account_info.get('account_number', '')}</AccountNumber>
    </AccountInfo>
    
    <IncomeDetails>
        <SalaryIncome>{summary.get('salary_income', 0)}</SalaryIncome>
        <OtherIncome>{summary.get('other_income', 0)}</OtherIncome>
        <GrossTotalIncome>{tax_calc['gross_total_income']}</GrossTotalIncome>
        <StandardDeduction>{tax_calc['standard_deduction']}</StandardDeduction>
        <TaxableIncome>{tax_calc['taxable_income']}</TaxableIncome>
    </IncomeDetails>
    
    <TaxCalculation>
        <TaxLiability>{tax_calc['tax_liability']}</TaxLiability>
    </TaxCalculation>
    
    <Transactions>
        {self._format_transactions_xml(transactions[:20])}
    </Transactions>
    
    <Summary>
        <TotalTransactions>{len(transactions)}</TotalTransactions>
        <TotalCredits>{summary.get('total_credits', 0)}</TotalCredits>
        <TotalDebits>{summary.get('total_debits', 0)}</TotalDebits>
    </Summary>
</ITR>"""
        
        return xml_content

    def _format_transactions_xml(self, transactions):
        """Format transactions for XML output"""
        if not transactions:
            return ""
        
        xml_transactions = []
        for txn in transactions:
            xml_transactions.append(f"""
        <Transaction>
            <Date>{txn.get('date', '')}</Date>
            <Description>{txn.get('description', '')}</Description>
            <Amount>{txn.get('amount', 0)}</Amount>
            <Type>{txn.get('type', '')}</Type>
        </Transaction>""")
        
        return ''.join(xml_transactions)
