# Quick Start Guide

## Prerequisites
- Python 3.11+
- pip package manager
- (Optional) Docker for containerized deployment

## Installation & Setup

### Step 1: Install Dependencies

```bash
cd finance_ml_api
pip install -r requirements.txt
```

### Step 2: Initialize Models

This will download and verify the pretrained BERT model:

```bash
python init_models.py
```

Expected output:
```
============================================================
Personal Finance ML API - Model Initialization
============================================================
✓ All core dependencies verified
✓ Kaleido (for plot export) verified
Initializing BERT model for zero-shot classification...
Model test successful! Predicted: Groceries
Confidence: 0.891
============================================================
✓ All models initialized successfully!
============================================================
```

### Step 3: Start the API Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The server will start at: `http://localhost:8000`

### Step 4: Test the API

Open your browser and go to:
- Interactive docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

Or use the test script:

```bash
python test_api.py path/to/your/bank_statement.pdf
```

## Using the API

### Method 1: Web Interface (Swagger UI)

1. Go to http://localhost:8000/docs
2. Click on "POST /process-pdf"
3. Click "Try it out"
4. Upload your PDF file
5. Click "Execute"
6. View the results

### Method 2: Command Line (curl)

```bash
curl -X POST "http://localhost:8000/process-pdf" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "pdf_file=@bank_statement.pdf" \
  -o response.json
```

### Method 3: Python Script

```python
import requests

with open('bank_statement.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/process-pdf',
        files={'pdf_file': f}
    )
    
result = response.json()
print(f"Total spend: ${result['summary']['total_spend']:.2f}")
```

## Understanding the Results

### Summary Section
- `total_transactions`: Number of transactions found
- `total_spend`: Total amount spent (expenses only)
- `period`: Date range of transactions
- `categories_detected`: Number of unique categories

### Categorization Section
- `categories`: List of all detected categories
- `avg_confidence`: Average confidence score (0-1)
- `top_categories`: Top 5 spending categories with amounts

### Anomalies Section
- `anomaly_rate`: Percentage of anomalous transactions
- `anomaly_transactions`: List of unusual transactions
- `largest_anomalies`: Top 10 most unusual expenses

### Forecast Section
- `next_month_forecasts`: Predicted spending per category for next month
- `avg_mae`: Average prediction error
- `major_categories`: Categories included in forecast

### Plots Section
- `category_pie`: Base64 encoded pie chart
- `anomaly_scatter`: Base64 encoded scatter plot
- `forecast_bar`: Base64 encoded bar chart

## Docker Deployment

### Build the image:
```bash
docker build -t finance-ml-api .
```

### Run the container:
```bash
docker run -p 8000:8000 finance-ml-api
```

### Test:
```bash
curl -X POST "http://localhost:8000/process-pdf" \
  -F "pdf_file=@bank_statement.pdf"
```

## Troubleshooting

### Issue: "No tables detected in PDF"
**Solution**: Ensure your PDF has tabular data. The PDF should be text-based, not scanned images.

### Issue: "Insufficient data for forecasting"
**Solution**: You need at least 6 months of transaction history for forecasting to work.

### Issue: "Cannot connect to API"
**Solution**: Make sure the server is running with `uvicorn app.main:app --host 0.0.0.0 --port 8000`

### Issue: "Kaleido not found"
**Solution**: Install kaleido with `pip install kaleido==0.2.1`

### Issue: Model download fails
**Solution**: Check your internet connection. The BERT model (~1.5GB) needs to download on first use.

## Performance Tips

1. **Batch Processing**: For multiple PDFs, send them sequentially rather than simultaneously
2. **GPU Acceleration**: Set `device=0` in bert_categorizer.py if you have a CUDA GPU
3. **Memory**: Expect ~2-3GB RAM usage with the BERT model loaded
4. **Response Time**: First request takes longer (~30-60s) due to model loading

## Next Steps

- Check out the full API documentation at `/docs`
- Explore the code in the `app/` directory
- Customize categories in `app/bert_categorizer.py`
- Adjust anomaly thresholds in `app/anomaly_detector.py`
- Tune forecasting parameters in `app/xgboost_forecaster.py`

## Support

For issues or questions:
1. Check the logs for error messages
2. Review the README.md for detailed documentation
3. Open an issue on GitHub with logs and sample data

