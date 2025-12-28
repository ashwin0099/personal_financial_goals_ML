"""
Configuration settings for the Personal Finance ML API
Modify these settings to customize the application behavior
"""
from pathlib import Path

# API Configuration
API_HOST = "0.0.0.0"
API_PORT = 8000

# Model Configuration
BERT_MODEL_NAME = "facebook/bart-large-mnli"
USE_GPU = False  # Set to True if CUDA is available
BATCH_SIZE = 8

# Forecasting Configuration
MIN_HISTORY_MONTHS = 6
FORECAST_MONTHS = 3
MAJOR_CATEGORY_THRESHOLD = 0.05  # Categories with >5% of total spending

# Anomaly Detection Configuration
Z_SCORE_THRESHOLD = 3.0

# Logging Configuration
LOG_LEVEL = "INFO"

# File Upload Configuration
MAX_FILE_SIZE_MB = 50

# Paths
BASE_DIR = Path(__file__).parent
MODEL_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "data"

# Ensure directories exist
MODEL_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

