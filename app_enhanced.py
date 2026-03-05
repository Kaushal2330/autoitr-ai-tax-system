import os
import json
from flask import Flask, request, render_template, jsonify, send_file
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from datetime import datetime
import logging

# Import services
from services.ocr_service import OCRService
try:
    from services.data_extraction_service import DataExtractionService
except ImportError:
    from services.data_extraction import DataExtractionService
from services.itr_generator import ITRGenerator
from services.validation_service import ValidationService
from utils.pdf_processor import PDFProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('generated', exist_ok=True)

# Initialize services
ocr_service = OCRService()
data_service = DataExtractionService()
itr_generator = ITRGenerator()
validator = ValidationService()
pdf_processor = PDFProcessor()

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Render the enhanced HTML template"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and processing"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file selected'}), 400

        file = request.files['file']
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Please upload PDF, PNG, JPG, or JPEG'}), 400

        # Save file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        logger.info(f"Processing file: {filepath}")

        # If encrypted, prompt for password
        try:
            if filename.lower().endswith('.pdf') and pdf_processor.is_encrypted(filepath):
                return jsonify({
                    'status': 'password_required',
                    'message': 'PDF is encrypted and requires a password',
                    'temp_path': filepath
                }), 200
        except Exception as e:
            logger.warning(f"Encryption check failed: {e}")

        # Process the file
        result = process_bank_statement(filepath)

        # Clean up uploaded file
        try:
            os.remove(filepath)
        except:
            pass

        return jsonify(result)

    except RequestEntityTooLarge:
        return jsonify({'error': 'File too large (max 16MB)'}), 413
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

def process_bank_statement(filepath):
    """Process the uploaded bank statement"""
    try:
        # Step 1: Extract text using OCR
        logger.info("Step 1: Extracting text...")
        extracted_text = ocr_service.extract_text(filepath)

        if not extracted_text or len(extracted_text.strip()) < 10:
            return {
                'status': 'error',
                'error': 'Could not extract sufficient text from document. Please ensure the file is a clear bank statement.',
                'suggestions': [
                    'Check if the file is a readable bank statement',
                    'Try a higher quality image or PDF',
                    'Ensure Tesseract OCR is properly installed'
                ]
            }

        logger.info(f"Extracted {len(extracted_text)} characters")

        # Step 2: Parse financial data (pass source path for table parsing)
        logger.info("Step 2: Parsing financial data...")
        financial_data = data_service.extract_financial_data(extracted_text, source_path=filepath)

        if not financial_data or 'error' in financial_data:
            return {
                'status': 'error',
                'error': financial_data.get('error', 'Failed to parse financial data'),
                'suggestions': [
                    'The document might not be a standard bank statement format',
                    'Try a different bank statement or file format'
                ]
            }

        if not financial_data.get('transactions'):
            return {
                'status': 'error',
                'error': 'No transactions found in the bank statement',
                'suggestions': [
                    'Ensure the document contains transaction history',
                    'Try a statement with more transaction details'
                ]
            }

        logger.info(f"Found {len(financial_data['transactions'])} transactions")

        # Step 3: Classify transactions
        logger.info("Step 3: Classifying transactions...")
        classified_data = data_service.classify_transactions(financial_data)

        # Step 4: Validate data
        logger.info("Step 4: Validating data...")
        validation_result = validator.validate_financial_data(classified_data)

        # Step 5: Generate ITR preview
        logger.info("Step 5: Generating ITR preview...")
        itr_preview = itr_generator.generate_itr_preview(classified_data)

        logger.info("Processing completed successfully")

        return {
            'status': 'success',
            'data': {
                'raw_transactions': financial_data.get('transactions', []),
                'classified_data': classified_data,
                'validation': validation_result,
                'itr_preview': itr_preview,
                'summary': classified_data.get('summary', {}),
                'account_info': classified_data.get('account_info', {}),
                'processing_info': {
                    'text_length': len(extracted_text),
                    'transactions_found': len(financial_data.get('transactions', [])),
                    'timestamp': datetime.now().isoformat(),
                    'debug': {
                        'text_rows_detected': financial_data.get('debug', {}).get('text_rows_detected'),
                        'table_rows_detected': financial_data.get('debug', {}).get('table_rows_detected'),
                    }
                }
            }
        }

    except Exception as e:
        logger.error(f"Processing error: {str(e)}")
        return {
            'status': 'error',
            'error': f'Processing failed: {str(e)}',
            'suggestions': [
                'Check if all dependencies are installed',
                'Verify the file is a valid bank statement',
                'Try a different file format or quality'
            ]
        }

@app.route('/generate_itr', methods=['POST'])
def generate_itr():
    """Generate final ITR file"""
    try:
        data = request.json
        user_info = data.get('user_info', {})
        financial_data = data.get('financial_data', {})
        format_type = data.get('format', 'json')

        # Generate ITR file
        itr_file_path = itr_generator.generate_itr_file(user_info, financial_data, format_type)

        return jsonify({
            'status': 'success',
            'file_path': itr_file_path,
            'download_url': f'/download/{os.path.basename(itr_file_path)}'
        })

    except Exception as e:
        logger.error(f"ITR generation error: {str(e)}")
        return jsonify({'error': f'ITR generation failed: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Download generated ITR file"""
    try:
        return send_file(
            os.path.join('generated', filename),
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({'error': 'File not found'}), 404

@app.route('/debug')
def debug_info():
    """Debug endpoint to check system status"""
    try:
        import pytesseract
        tesseract_version = "Installed"
        try:
            tesseract_version = str(pytesseract.get_tesseract_version())
        except:
            tesseract_version = "Error getting version"
    except ImportError:
        tesseract_version = "Not installed"

    return jsonify({
        'tesseract_ocr': tesseract_version,
        'upload_folder': app.config['UPLOAD_FOLDER'],
        'upload_folder_exists': os.path.exists(app.config['UPLOAD_FOLDER']),
        'max_file_size': f"{app.config['MAX_CONTENT_LENGTH'] / (1024*1024):.1f} MB",
        'allowed_extensions': list(ALLOWED_EXTENSIONS),
        'services_status': {
            'ocr_service': 'Initialized',
            'data_extraction': 'Initialized',
            'itr_generator': 'Initialized',
            'validator': 'Initialized'
        }
    })

@app.route('/unlock_pdf', methods=['POST'])
def unlock_pdf():
    """Unlock an encrypted PDF using user-provided password and process it."""
    try:
        data = request.json or {}
        temp_path = data.get('temp_path')
        password = data.get('password', '')
        if not temp_path or not os.path.exists(temp_path):
            return jsonify({'error': 'Temporary PDF path not found'}), 400
        if not password:
            return jsonify({'error': 'Password is required'}), 400

        # Attempt unlock
        unlocked_path = pdf_processor.unlock_pdf(temp_path, password)
        logger.info(f"Unlocked PDF at: {unlocked_path}")

        # Process unlocked PDF
        result = process_bank_statement(unlocked_path)

        # Clean up both temp files
        try:
            os.remove(temp_path)
        except Exception:
            pass
        if unlocked_path != temp_path:
            try:
                os.remove(unlocked_path)
            except Exception:
                pass

        return jsonify(result)
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 401
    except Exception as e:
        logger.error(f"Unlock error: {str(e)}")
        return jsonify({'error': f'Unlock failed: {str(e)}'}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("AutoITR - Enhanced Frontend Version")
    print("=" * 60)
    print("🎨 Modern responsive UI with drag-and-drop upload")
    print("⚡ Real-time processing feedback and animations")
    print("📊 Enhanced data visualization and results display")
    print("🔍 Visit /debug to check system status")
    print("=" * 60)
    print("\n🌐 Application available at: http://localhost:5000")

    app.run(debug=True, host='0.0.0.0', port=5000)
