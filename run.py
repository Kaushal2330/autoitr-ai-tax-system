#!/usr/bin/env python3
import os
import sys

def main():
    print("AutoITR - AI-Powered Tax Filing System")
    print("=" * 50)

    # Create directories
    os.makedirs('static/uploads', exist_ok=True)
    os.makedirs('generated', exist_ok=True)

    try:
        from app import app
        print("Starting application at http://localhost:5000")
        app.run(debug=True, host='0.0.0.0', port=5000)
    except ImportError as e:
        print(f"Error: {e}")
        print("Make sure all dependencies are installed:")
        print("pip install -r requirements.txt")
        sys.exit(1)

if __name__ == "__main__":
    main()
