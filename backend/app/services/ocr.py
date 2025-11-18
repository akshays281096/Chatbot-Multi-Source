"""
OCR service for extracting text from images and PDFs
"""
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import logging
from typing import List, Dict
import os

logger = logging.getLogger(__name__)


class OCRService:
    """OCR service for text extraction from images"""
    
    @staticmethod
    def extract_text_from_image(image_path: str) -> str:
        """Extract text from an image file"""
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            logger.info(f"Extracted {len(text)} characters from image")
            return text
        except Exception as e:
            logger.error(f"Error extracting text from image {image_path}: {e}")
            raise
    
    @staticmethod
    def extract_text_from_pdf_images(pdf_path: str) -> List[Dict[str, str]]:
        """Extract text from PDF using OCR (for scanned PDFs)"""
        chunks = []
        try:
            # Convert PDF pages to images
            images = convert_from_path(pdf_path)
            
            for page_num, image in enumerate(images):
                text = pytesseract.image_to_string(image)
                if text.strip():
                    chunks.append({
                        'text': text,
                        'metadata': {
                            'source_type': 'pdf_ocr',
                            'source': os.path.basename(pdf_path),
                            'page': page_num + 1
                        }
                    })
            
            logger.info(f"Extracted text from {len(chunks)} PDF pages using OCR")
            return chunks
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
            raise


def extract_text_from_image(image_path: str) -> str:
    """Convenience function for extracting text from image"""
    return OCRService.extract_text_from_image(image_path)

