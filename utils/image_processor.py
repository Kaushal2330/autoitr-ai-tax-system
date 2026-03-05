import cv2
import numpy as np
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class ImageProcessor:
    def preprocess_for_ocr(self, image_path):
        try:
            if isinstance(image_path, str):
                image = cv2.imread(image_path)
            else:
                image = image_path

            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Apply threshold
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Convert back to PIL
            return Image.fromarray(binary)
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            return Image.open(image_path) if isinstance(image_path, str) else image_path
