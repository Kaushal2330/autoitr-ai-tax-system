
import os
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime
import logging

# Import services
from services.ocr_service import OCRService
from kotak_enhanced_extraction import EnhancedDataExtractionService

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ocr_service = OCRService()
data_service = EnhancedDataExtractionService()

@app.route('/')
def index():
    return """
    <html>
    <head><title>Kotak Statement Debug</title></head>
    <body style="font-family: Arial; margin: 40px;">
        <h1 style="color: #dc143c;">🏦 Kotak Bank Statement Debug</h1>
        <p>Upload your Kotak statement to diagnose reading issues:</p>

        <form id="form" enctype="multipart/form-data">
            <div style="border: 2px dashed #dc143c; padding: 20px; text-align: center; margin: 20px 0;">
                <input type="file" id="file" accept=".pdf,.png,.jpg,.jpeg" required>
                <p>Select your Kotak bank statement</p>
            </div>
            <button type="submit" style="background: #dc143c; color: white; padding: 10px 20px; border: none; cursor: pointer;">
                🔍 Debug Statement
            </button>
        </form>

        <div id="results" style="margin-top: 20px;"></div>

        <script>
        document.getElementById('form').onsubmit = async function(e) {
            e.preventDefault();
            const formData = new FormData();
            formData.append('file', document.getElementById('file').files[0]);

            document.getElementById('results').innerHTML = '<p>🔍 Analyzing...</p>';

            try {
                const response = await fetch('/debug', {method: 'POST', body: formData});
                const result = await response.json();

                let html = '';
                if (result.status === 'success') {
                    html = '<div style="color: green; background: #f0fff0; padding: 15px; border-left: 4px solid green;">';
                    html += '<h3>✅ Success! Found ' + result.data.summary.total_transactions + ' transactions</h3>';
                    html += '<p>Credits: ₹' + (result.data.summary.total_credits || 0).toLocaleString() + '</p>';
                    html += '<p>Debits: ₹' + (result.data.summary.total_debits || 0).toLocaleString() + '</p>';
                    html += '</div>';

                    if (result.data.transactions.length > 0) {
                        html += '<h4>Sample Transactions:</h4><table border="1" style="width:100%; border-collapse: collapse;">';
                        html += '<tr><th>Date</th><th>Description</th><th>Amount</th><th>Type</th></tr>';
                        result.data.transactions.slice(0, 5).forEach(t => {
                            html += '<tr><td>' + t.date + '</td><td>' + t.description.substring(0,50) + '</td><td>₹' + t.amount + '</td><td>' + t.type + '</td></tr>';
                        });
                        html += '</table>';
                    }
                } else {
                    html = '<div style="color: red; background: #fff0f0; padding: 15px; border-left: 4px solid red;">';
                    html += '<h3>❌ Error: ' + result.error + '</h3>';

                    if (result.debug_info) {
                        html += '<h4>Debug Info:</h4>';
                        if (result.debug_info.text_length) {
                            html += '<p>Text Length: ' + result.debug_info.text_length + ' characters</p>';
                        }
                        if (result.debug_info.kotak_keywords) {
                            html += '<p>Kotak Keywords Found: ' + result.debug_info.kotak_keywords.join(', ') + '</p>';
                        }
                        if (result.debug_info.text_preview) {
                            html += '<h4>Text Preview:</h4><pre style="background: #f8f9fa; padding: 10px;">' + result.debug_info.text_preview + '</pre>';
                        }

                        html += '<h4>💡 Suggestions:</h4><ul>';
                        html += '<li>Ensure file is a genuine Kotak bank statement</li>';
                        html += '<li>Check if PDF is password-protected</li>';
                        html += '<li>Try better quality image if using photo</li>';
                        html += '<li>Verify statement contains transaction details</li>';
                        html += '</ul>';
                    }
                    html += '</div>';
                }

                document.getElementById('results').innerHTML = html;
            } catch (error) {
                document.getElementById('results').innerHTML = '<div style="color: red;">Error: ' + error.message + '</div>';
            }
        };
        </script>
    </body>
    </html>
    """

@app.route('/debug', methods=['POST'])
def debug_statement():
    try:
        logger.info("=== KOTAK DEBUG STARTED ===")

        if 'file' not in request.files:
            return jsonify({'status': 'error', 'error': 'No file uploaded'})

        file = request.files['file']
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"debug_{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        logger.info(f"Processing: {filepath}")

        # Extract text
        extracted_text = ocr_service.extract_text(filepath)

        if isinstance(extracted_text, dict):
            if extracted_text.get('status') == 'password_required':
                return jsonify({
                    'status': 'error',
                    'error': 'PDF is password-protected. Please unlock first.',
                    'debug_info': {'text_extraction': 'password_required'}
                })
            elif extracted_text.get('status') != 'success':
                return jsonify({
                    'status': 'error',
                    'error': extracted_text.get('message', 'Text extraction failed'),
                    'debug_info': {'text_extraction': 'failed'}
                })
            extracted_text = extracted_text['text']

        logger.info(f"Extracted {len(extracted_text)} characters")

        if not extracted_text or len(extracted_text.strip()) < 10:
            return jsonify({
                'status': 'error',
                'error': 'Could not extract sufficient text',
                'debug_info': {
                    'text_length': len(extracted_text) if extracted_text else 0,
                    'text_preview': extracted_text[:200] if extracted_text else ''
                }
            })

        # Extract financial data
        financial_data = data_service.extract_financial_data(extracted_text)

        # Clean up file
        try:
            os.remove(filepath)
        except:
            pass

        if 'error' in financial_data:
            return jsonify({
                'status': 'error',
                'error': financial_data['error'],
                'debug_info': financial_data.get('debug_info', {})
            })

        return jsonify({
            'status': 'success',
            'data': financial_data
        })

    except Exception as e:
        logger.error(f"Debug failed: {e}")
        return jsonify({
            'status': 'error',
            'error': f'Debug failed: {str(e)}'
        })

if __name__ == '__main__':
    print("🏦 Kotak Debug Tool Starting...")
    print("Visit: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
