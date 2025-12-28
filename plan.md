# Step-by-Step Execution Plan for Personal Finance ML API
This execution plan provides sequential, unambiguous instructions for code generation. Follow **exactly** in order without deviations.
## Phase 1: Project Structure & Dependencies
```
Create directory: finance_ml_api/
Inside finance_ml_api/, create:
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── pdf_extractor.py
│   ├── bert_categorizer.py
│   ├── anomaly_detector.py
│   └── xgboost_forecaster.py
├── models/
├── data/
├── requirements.txt
├── Dockerfile
└── README.md
```
**requirements.txt contents** (exact versions for reproducibility):
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
camelot-py[cv]==0.2.1
pandas==2.1.4
numpy==1.24.3
scikit-learn==1.3.2
xgboost==2.0.3
sentence-transformers==2.2.2
plotly==5.17.0
python-multipart==0.0.6
opencv-python==4.8.1.78
ghostscript==0.7
pypdfium2==4.25.0
joblib==1.3.2
```
## Phase 2: PDF Extractor Module (app/pdf_extractor.py)
**Input**: Multi-page PDF bank statement
**Output**: Cleaned pandas DataFrame saved as parquet
**Step-by-step logic**:
1. Import: `camelot, pandas, numpy, io`
2. Define function `extract_transactions(pdf_path: str) -> pd.DataFrame`
3. Use `camelot.read_pdf(pdf_path, backend='lattice', pages='all', flavor='lattice')`
4. Concat all tables: `dfs = pd.concat([table.df for table in tables], ignore_index=True)`
5. Hardcoded column mapping (index-based):
   - Col 0: `transaction_date`
   - Col 1: `particulars`
   - Col 2: `credited_amount`
   - Col 3: `debited_amount`
   - Col 4: `balance`
6. Parse dates: `df['transaction_date'] = pd.to_datetime(df[0], format='%d-%m-%Y', errors='coerce')`
7. Forward fill ALL columns: `df = df.fillna(method='ffill').fillna(method='bfill')`
8. Numeric conversion: `df[[2,3,4]] = df[[2,3,4]].apply(pd.to_numeric, errors='coerce')`
9. Calculate `net_amount = df[2] - df[3]` (negative for expenses)
10. Filter: `df = df[(df['net_amount'].abs() > 0) & (df['transaction_date'].notna())]`
11. Add features: `month`, `year`, `day_of_week` from `transaction_date.dt`
12. Rename columns: `['date', 'desc', 'credit', 'debit', 'balance', 'net_amount', 'month', 'year', 'day_of_week']`
13. Return `df.sort_values('date').reset_index(drop=True)`
## Phase 3: BERT Categorizer Module (app/bert_categorizer.py)
**Input**: DataFrame with 'desc' column
**Output**: DataFrame with 'category', 'confidence' + model metrics
**Step-by-step logic**:
1. Import: `sentence_transformers, sklearn.linear_model, sklearn.metrics, sklearn.model_selection, numpy`
2. Load model: `model = SentenceTransformer('sentence-transformers/bert-base-nli-mean-tokens')`
3. Define 15 categories **exactly**:
   ```
   ['Food', 'Groceries', 'Transport', 'Bills_Utilities', 'Shopping',
    'Entertainment', 'Healthcare', 'Education', 'Travel', 'Insurance',
    'Investment', 'Salary_Income', 'Transfer', 'ATM_Withdrawal', 'Other']
   ```
4. Preprocess descriptions: lowercase, strip punctuation/whitespace
5. Generate embeddings: `embeddings = model.encode(descriptions, batch_size=32, show_progress_bar=True)`
6. **Training data generation** (synthetic for demo):
   - Create keyword mapping dict (50 descriptions per category)
   - Generate labels from keywords in descriptions
7. Train LogisticRegression: `C=1.0, max_iter=1000, class_weight='balanced'`
8. 80/20 train/test split, compute **macro F1-score**
9. Predict on full dataset: `categories, probabilities = model.predict(X), model.predict_proba(X)`
10. Add columns: `df['category'] = categories`, `df['confidence'] = probabilities.max(axis=1)`
11. Save model: `joblib.dump(model, 'models/bert_categorizer.pkl')`
## Phase 4: Anomaly Detector Module (app/anomaly_detector.py)
**Input**: Categorized DataFrame
**Output**: Anomaly transactions list + stats
**Step-by-step logic**:
1. Import: `numpy, scipy.stats, pandas`
2. Filter expenses: `expenses = df[df['net_amount'] < 0].copy()`
3. Group by category: `grouped = expenses.groupby('category')['net_amount'].abs()`
4. Per category compute: `mean = grouped.mean()`, `std = grouped.std()`
5. Calculate Z-scores: `z_scores = (amounts - mean[cat]) / std[cat]`
6. Flag anomalies: `abs_z > 3.0`
7. Extract top anomalies: sort by `abs(z_score)`, take top 10%
8. Compute stats: `anomaly_rate = anomalies.shape[0] / expenses.shape[0]`
9. Return dict: `anomalies_df.to_dict('records'), anomaly_rate, largest_anomalies`
## Phase 5: XGBoost Forecaster Module (app/xgboost_forecaster.py)
**Input**: Categorized transaction DataFrame
**Output**: Next 3 months forecasts per category
**Step-by-step logic**:
1. Import: `xgboost as xgb, sklearn.model_selection.TimeSeriesSplit, pandas`
2. Aggregate monthly: `monthly = df[df.net_amount<0].groupby(['year','month','category'])['net_amount'].sum().unstack(fill_value=0)`
3. Create time-series DF: rows=months, columns=category totals
4. Features **exactly**:
   - `lag_1 = monthly.shift(1)`, `lag_2=shift(2)`, `lag_3=shift(3)`
   - `rolling_3m = monthly.rolling(3).mean()`
   - `month_sin = np.sin(2*np.pi*month_num/12)`
   - `total_trend = monthly.sum(axis=1).pct_change()`
5. For each major category (>5% total spend): train separate model
6. Model: `XGBRegressor(n_estimators=200, max_depth=6, learning_rate=0.1, random_state=42)`
7. Cross-validation: `TimeSeriesSplit(n_splits=5)`
8. Metrics: MAE on test set
9. Predict next 3 months using recursive forecasting
10. Save: `joblib.dump(model, f'models/xgb_{category}.pkl')`
## Phase 6: FastAPI Backend (app/main.py)
**Structure**:
1. Import all modules + `fastapi, plotly.graph_objects as go, base64, io`
2. Create `app = FastAPI()`
3. **Single endpoint**: `POST /process-pdf`
   - `UploadFile pdf_file: UploadFile`
   - `async def process_pdf(pdf_file: UploadFile)`
4. Pipeline sequence:
   ```
   1. Save uploaded PDF to temp file
   2. extract_transactions(pdf_path)
   3. bert_categorizer(transactions_df)
   4. anomaly_detector(categorized_df)
   5. xgboost_forecaster(categorized_df)
   6. Generate 3 Plotly plots:
      - Category pie chart (spend shares)
      - Anomaly scatter (date vs amount, red=anomaly)
      - Forecast bar (actual vs predicted next 3 months)
   7. Convert plots to base64 PNG: fig.to_image(format="png")
   ```
**Response JSON structure** (exact keys):
```json
{
  "summary": {"total_transactions": int, "total_spend": float, "period": "YYYY-YYYY"},
  "categorization": {"categories": list, "f1_score": float, "top_categories": dict},
  "anomalies": {"anomaly_transactions": list, "anomaly_rate": float, "largest_anomalies": list},
  "forecast": {"next_month_forecasts": dict, "mae": float, "major_categories": list},
  "plots": {
    "category_pie": "data:image/png;base64,...",
    "anomaly_scatter": "data:image/png;base64,...",
    "forecast_bar": "data:image/png;base64,..."
  }
}
```
## Phase 7: Docker & Deployment
**Dockerfile contents**:
```
FROM python:3.11-slim
RUN apt-get update && apt-get install -y ghostscript python3-tk
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
**Run commands**:
```
docker build -t finance-ml-api .
docker run -p 8000:8000 finance-ml-api
curl -X POST "http://localhost:8000/process-pdf" -F "pdf_file=@bank_statement.pdf"
```
## Phase 8: Validation Checklist
**Success criteria** (code generator must verify):
- [ ] PDF extraction recovers >95% transactions
- [ ] BERT F1-score ≥0.82 on validation set
- [ ] XGBoost MAE ≤15% median monthly spend
- [ ] API responds <30s with valid base64 plots
- [ ] All 15 categories detected
- [ ] Z-score anomalies flagged correctly
- [ ] Docker container runs without errors
**Execute phases sequentially**. Each phase must complete successfully before next. No code deviations permitted.