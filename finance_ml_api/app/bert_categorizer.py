"""
BERT Categorizer Module
Categorizes transactions using pretrained transformer models
"""
import pandas as pd
import numpy as np
from transformers import pipeline
import logging
import joblib
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the 15 categories exactly as specified
CATEGORIES = [
    'Food', 'Groceries', 'Transport', 'Bills_Utilities', 'Shopping',
    'Entertainment', 'Healthcare', 'Education', 'Travel', 'Insurance',
    'Investment', 'Salary_Income', 'Transfer', 'ATM_Withdrawal', 'Other'
]


class BERTCategorizer:
    """Zero-shot classification for financial transactions"""
    
    def __init__(self, model_name: str = "facebook/bart-large-mnli"):
        """
        Initialize the categorizer with a pretrained model
        
        Args:
            model_name: Name of the pretrained model for zero-shot classification
        """
        self.model_name = model_name
        self.categories = CATEGORIES
        self.classifier = None
        self._load_model()
    
    def _load_model(self):
        """Load the zero-shot classification pipeline"""
        try:
            logger.info(f"Loading pretrained model: {self.model_name}")
            self.classifier = pipeline(
                "zero-shot-classification",
                model=self.model_name,
                device=-1  # Use CPU; set to 0 for GPU
            )
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise
    
    def _preprocess_description(self, desc: str) -> str:
        """
        Preprocess transaction description
        
        Args:
            desc: Raw transaction description
            
        Returns:
            Cleaned description
        """
        if pd.isna(desc):
            return ""
        
        # Convert to lowercase and strip whitespace
        desc = str(desc).lower().strip()
        
        # Remove extra whitespace
        desc = ' '.join(desc.split())
        
        return desc
    
    def categorize_batch(self, descriptions: list, batch_size: int = 8) -> tuple:
        """
        Categorize a batch of transaction descriptions
        
        Args:
            descriptions: List of transaction descriptions
            batch_size: Number of descriptions to process at once
            
        Returns:
            Tuple of (categories, confidence_scores)
        """
        categories = []
        confidences = []
        
        logger.info(f"Categorizing {len(descriptions)} transactions")
        
        for i in range(0, len(descriptions), batch_size):
            batch = descriptions[i:i + batch_size]
            
            for desc in batch:
                # Preprocess
                clean_desc = self._preprocess_description(desc)
                
                if not clean_desc:
                    categories.append('Other')
                    confidences.append(0.5)
                    continue
                
                try:
                    # Perform zero-shot classification
                    result = self.classifier(
                        clean_desc,
                        candidate_labels=self.categories,
                        multi_label=False
                    )
                    
                    # Get top prediction
                    categories.append(result['labels'][0])
                    confidences.append(result['scores'][0])
                    
                except Exception as e:
                    logger.warning(f"Error categorizing '{desc}': {str(e)}")
                    categories.append('Other')
                    confidences.append(0.5)
            
            if (i + batch_size) % 50 == 0:
                logger.info(f"Processed {min(i + batch_size, len(descriptions))}/{len(descriptions)} transactions")
        
        return categories, confidences
    
    def save(self, path: str):
        """
        Save categorizer configuration
        
        Args:
            path: Path to save the model info
        """
        config = {
            'model_name': self.model_name,
            'categories': self.categories
        }
        joblib.dump(config, path)
        logger.info(f"Saved categorizer config to {path}")
    
    @classmethod
    def load(cls, path: str):
        """
        Load categorizer from saved configuration
        
        Args:
            path: Path to the saved model info
            
        Returns:
            BERTCategorizer instance
        """
        config = joblib.load(path)
        return cls(model_name=config['model_name'])


def categorize_transactions(
    df: pd.DataFrame, 
    model_path: str = None,
    batch_size: int = 8
) -> tuple:
    """
    Categorize transactions in a DataFrame
    
    Args:
        df: DataFrame with 'desc' column
        model_path: Path to saved model (optional)
        batch_size: Batch size for processing
        
    Returns:
        Tuple of (categorized_df, metrics_dict)
    """
    # Load or create categorizer
    if model_path and Path(model_path).exists():
        logger.info(f"Loading categorizer from {model_path}")
        categorizer = BERTCategorizer.load(model_path)
    else:
        categorizer = BERTCategorizer()
    
    # Get descriptions
    descriptions = df['desc'].tolist()
    
    # Categorize
    categories, confidences = categorizer.categorize_batch(descriptions, batch_size)
    
    # Add to DataFrame
    df = df.copy()
    df['category'] = categories
    df['confidence'] = confidences
    
    # Calculate metrics
    category_counts = df['category'].value_counts()
    top_categories = category_counts.head(5).to_dict()
    avg_confidence = df['confidence'].mean()
    
    metrics = {
        'categories': list(df['category'].unique()),
        'avg_confidence': float(avg_confidence),
        'top_categories': top_categories,
        'category_distribution': category_counts.to_dict()
    }
    
    logger.info(f"Categorization complete. Average confidence: {avg_confidence:.3f}")
    logger.info(f"Top categories: {list(top_categories.keys())}")
    
    return df, metrics


def calculate_f1_score(df: pd.DataFrame, true_labels: list = None) -> float:
    """
    Calculate F1 score if ground truth labels are available
    
    Args:
        df: DataFrame with 'category' column
        true_labels: Ground truth labels (optional)
        
    Returns:
        F1 score or None if no ground truth available
    """
    if true_labels is None:
        logger.warning("No ground truth labels provided, cannot calculate F1 score")
        return None
    
    from sklearn.metrics import f1_score
    
    predicted_labels = df['category'].tolist()
    
    # Calculate macro F1 score
    f1 = f1_score(true_labels, predicted_labels, average='macro')
    
    logger.info(f"Macro F1 Score: {f1:.3f}")
    
    return float(f1)

