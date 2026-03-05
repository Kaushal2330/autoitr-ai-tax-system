# AutoITR - AI-Powered Income Tax Return Filing

AutoITR automatically processes bank statements and generates ITR files using AI.

## Features

- AI-powered OCR text extraction
- Transaction classification using ML
- Automated ITR form generation
- Data validation and quality checks
- Secure local processing

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install PyMuPDF
   ```

2. Install Tesseract OCR:
   - Windows: Download from GitHub
   - Linux: sudo apt install tesseract-ocr  
   - macOS: brew install tesseract

3. Run application:
   ```bash
   python app.py
   ```

4. Open http://localhost:5000

## Project Structure

- app.py - Main Flask application
- services/ - Core business logic
- utils/ - Utility classes  
- models/ - Data models
- static/ - Web assets

## Important Notes

- All processing is local
- Verify generated data before filing
- For convenience only - consult tax professionals

## Support

Check logs for errors and ensure all dependencies are installed.
