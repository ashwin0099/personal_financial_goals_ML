# Personal Finance ML API

A comprehensive AI-powered API for analyzing bank statements using machine learning. This application extracts transaction data from PDF bank statements, categorizes transactions using BERT-based zero-shot classification, detects spending anomalies, and forecasts future spending patterns using XGBoost.

## Features

### 🔍 PDF Transaction Extraction
- Extracts transaction data from multi-page bank statement PDFs
- Handles various date formats and currency symbols
- Cleans and validates transaction data

### 🏷️ AI-Powered Categorization
- Uses pretrained BERT models for zero-shot transaction categorization
- 15 predefined categories including Food, Groceries, Transport, Bills, Shopping, etc.
- Provides confidence scores for each categorization

### 🚨 Anomaly Detection
- Statistical Z-score based anomaly detection
- Identifies unusual spending patterns per category
- Highlights largest anomalies with context

### 📈 Spending Forecasting
- XGBoost-based time series forecasting
- Predicts next 3 months of spending by category
- Uses lag features, rolling statistics, and seasonal components

### 📊 Rich Visualizations
- Category spending distribution (pie chart)
- Anomaly scatter plot over time
- Spending forecast comparison (bar chart)

## Project Structure

```
finance_ml_api/
├── app/
│   ├── __init__.py              # Package initialization
│   ├── main.py                  # FastAPI application
│   ├── pdf_extractor.py         # PDF extraction module
│   ├── bert_categorizer.py      # Transaction categorization
│   ├── anomaly_detector.py      # Anomaly detection
│   └── xgboost_forecaster.py    # Spending forecasting
├── models/                       # Saved ML models
├── data/                         # Data directory
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Docker configuration
└── README.md                     # This file
```

## Installation

### Option 1: Local Installation

1. **Clone the repository**
```bash
cd finance_ml_api
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run the application**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Option 2: Docker Installation

1. **Build the Docker image**
```bash
docker build -t finance-ml-api .
```

2. **Run the container**
```bash
docker run -p 8000:8000 finance-ml-api
```

## Usage

### API Endpoints

#### `GET /`
Root endpoint with API information

#### `GET /health`
Health check endpoint

#### `POST /process-pdf`
Upload and analyze a bank statement PDF

**Request:**
```bash
curl -X POST "http://localhost:8000/process-pdf" \
  -F "pdf_file=@bank_statement.pdf"
```

**Response:**
```json
{
  "summary": {
    "total_transactions": 150,
    "total_spend": 4500.50,
    "period": "2023-2024",
    "categories_detected": 12
  },
  "categorization": {
    "categories": ["Food", "Groceries", "Transport", ...],
    "avg_confidence": 0.85,
    "top_categories": {
      "Groceries": 1200.50,
      "Transport": 800.00,
      "Food": 650.25
    }
  },
  "anomalies": {
    "anomaly_transactions": [...],
    "anomaly_rate": 0.08,
    "largest_anomalies": [...],
    "total_anomalies": 12
  },
  "forecast": {
    "next_month_forecasts": {
      "Groceries": 420.50,
      "Transport": 280.00
    },
    "avg_mae": 45.20,
    "major_categories": ["Groceries", "Transport", "Food"]
  },
  "plots": {
    "category_pie": "data:image/png;base64,...",
    "anomaly_scatter": "data:image/png;base64,...",
    "forecast_bar": "data:image/png;base64,..."
  }
}
```

### Interactive API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Technical Details

### Transaction Categories

The system categorizes transactions into 15 predefined categories:
1. Food - Restaurant and dining expenses
2. Groceries - Supermarket purchases
3. Transport - Commute and travel costs
4. Bills_Utilities - Electricity, water, internet, etc.
5. Shopping - Retail purchases
6. Entertainment - Movies, games, subscriptions
7. Healthcare - Medical expenses
8. Education - Courses, books, tuition
9. Travel - Vacation and trip expenses
10. Insurance - Insurance premiums
11. Investment - Savings and investments
12. Salary_Income - Income deposits
13. Transfer - Money transfers
14. ATM_Withdrawal - Cash withdrawals
15. Other - Miscellaneous transactions

### Machine Learning Models

#### BERT Categorization
- Model: `facebook/bart-large-mnli`
- Method: Zero-shot classification
- No training data required
- Confidence scores provided for each prediction

#### XGBoost Forecasting
- Algorithm: XGBoost Regressor
- Features: Lag features (1-3 months), rolling statistics, seasonal components
- Validation: Time series cross-validation
- Metric: Mean Absolute Error (MAE)

#### Anomaly Detection
- Method: Statistical Z-score analysis
- Threshold: |Z-score| > 3.0
- Per-category analysis for context-aware detection

### Data Requirements

For optimal results:
- **Minimum transactions**: 50+ transactions
- **Time period**: At least 6 months of history
- **PDF format**: Tabular bank statements with date, description, credit, debit, balance columns

## Error Handling

The API includes comprehensive error handling for:
- Invalid PDF format or missing tables
- Insufficient transaction data
- Failed categorization or forecasting
- Visualization generation errors

All errors return appropriate HTTP status codes and detailed error messages.

## Performance

- **PDF Processing**: ~5-10 seconds for 100 transactions
- **Categorization**: ~1-2 seconds per 10 transactions
- **Forecasting**: ~3-5 seconds for model training
- **Total API Response**: <30 seconds for typical bank statements

## Dependencies

Key dependencies include:
- FastAPI - Web framework
- Uvicorn - ASGI server
- Camelot - PDF table extraction
- Transformers - BERT models
- XGBoost - Forecasting
- Plotly - Visualizations
- Pandas, NumPy, Scikit-learn - Data processing and ML

See `requirements.txt` for complete list with versions.

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format code
black app/

# Lint code
flake8 app/

# Type checking
mypy app/
```

## Limitations

- Assumes standard tabular bank statement format
- PDF extraction may fail on image-based or non-standard formats
- Forecasting requires at least 6 months of historical data
- Zero-shot classification may be less accurate than fine-tuned models

## Future Enhancements

- [ ] Support for multiple bank statement formats
- [ ] Fine-tuned transaction categorization model
- [ ] Multi-currency support
- [ ] Budget tracking and alerts
- [ ] Export reports in PDF/Excel format
- [ ] User accounts and transaction history
- [ ] Mobile app integration

## License

MIT License - See LICENSE file for details

## Support

For issues or questions, please open an issue on the GitHub repository.

---

**Built with ❤️ using FastAPI, BERT, and XGBoost**

