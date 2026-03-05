import logging

logger = logging.getLogger(__name__)

class ValidationService:
    def validate_financial_data(self, classified_data):
        try:
            validation = {
                'overall_status': 'valid',
                'warnings': [],
                'errors': [],
                'data_quality_score': 85
            }

            transactions = classified_data.get('transactions', [])
            if not transactions:
                validation['errors'].append('No transactions found')
                validation['overall_status'] = 'invalid'

            return validation
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {'overall_status': 'error', 'errors': [str(e)]}
