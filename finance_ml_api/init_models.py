"""
Model Initialization Script
Pre-downloads and verifies ML models
"""
import logging
from pathlib import Path
from transformers import pipeline
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent / "models"
MODEL_DIR.mkdir(exist_ok=True)


def initialize_bert_model():
    """Download and initialize BERT model for categorization"""
    try:
        logger.info("Initializing BERT model for zero-shot classification...")
        model_name = "facebook/bart-large-mnli"
        
        classifier = pipeline(
            "zero-shot-classification",
            model=model_name,
            device=-1  # CPU
        )
        
        # Test with a sample transaction
        test_result = classifier(
            "Payment to Walmart Supercenter",
            candidate_labels=["Food", "Groceries", "Shopping"],
            multi_label=False
        )
        
        logger.info(f"Model test successful! Predicted: {test_result['labels'][0]}")
        logger.info(f"Confidence: {test_result['scores'][0]:.3f}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error initializing BERT model: {str(e)}")
        return False


def verify_dependencies():
    """Verify all required dependencies are installed"""
    try:
        logger.info("Verifying dependencies...")
        
        import fastapi
        import uvicorn
        import camelot
        import pandas
        import numpy
        import sklearn
        import xgboost
        import plotly
        import transformers
        import torch
        
        logger.info("✓ All core dependencies verified")
        
        # Check optional dependencies
        try:
            import kaleido
            logger.info("✓ Kaleido (for plot export) verified")
        except ImportError:
            logger.warning("⚠ Kaleido not found - plot export may not work")
        
        return True
        
    except ImportError as e:
        logger.error(f"Missing dependency: {str(e)}")
        logger.error("Please run: pip install -r requirements.txt")
        return False


def main():
    """Main initialization function"""
    logger.info("=" * 60)
    logger.info("Personal Finance ML API - Model Initialization")
    logger.info("=" * 60)
    
    # Verify dependencies
    if not verify_dependencies():
        logger.error("Dependency verification failed!")
        sys.exit(1)
    
    logger.info("")
    
    # Initialize BERT model
    if not initialize_bert_model():
        logger.error("BERT model initialization failed!")
        sys.exit(1)
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("✓ All models initialized successfully!")
    logger.info("=" * 60)
    logger.info("")
    logger.info("You can now run the API with:")
    logger.info("  uvicorn app.main:app --host 0.0.0.0 --port 8000")
    logger.info("")


if __name__ == "__main__":
    main()

