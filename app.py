import os
import json
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime
import logging

# Import services
from services.ocr_service import OCRService
from services.data_extraction import DataExtractionService
from services.itr_generator import ITRGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize services
ocr_service = OCRService()
data_service = DataExtractionService()
itr_generator = ITRGenerator()

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return '''<!DOCTYPE html>
<html>
<head><title>AutoITR - AI Tax Filing</title></head>
<body>
    <h1>AutoITR - AI-Powered Income Tax Filing</h1>
    <form method="post" action="/upload" enctype="multipart/form-data">
        <input type="file" name="file" accept=".pdf,.png,.jpg,.jpeg" required>
        <button type="submit">Process Bank Statement</button>
    </form>
</body>
</html>'''

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file selected'}), 400

        file = request.files['file']
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file'}), 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Process file
        result = process_bank_statement(filepath)

        # Clean up
        os.remove(filepath)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def process_bank_statement(filepath):
    try:
        # Extract text
        text = ocr_service.extract_text(filepath)
        if not text:
            return {'error': 'Could not extract text'}

        # Parse data
        data = data_service.extract_financial_data(text)
        if not data:
            return {'error': 'Could not parse data'}

        # Generate ITR
        itr = itr_generator.generate_itr_preview(data)

        return {
            'status': 'success',
            'data': data,
            'itr_preview': itr
        }
    except Exception as e:
        return {'error': str(e)}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
