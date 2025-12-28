"""
FastAPI Main Application
Personal Finance ML API for analyzing bank statements
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import tempfile
import shutil
import base64
import io
import logging
import uuid
from datetime import datetime

from app.pdf_extractor import extract_transactions
from app.bert_categorizer import categorize_transactions, CATEGORIES
from app.anomaly_detector import detect_anomalies, get_spending_insights
from app.xgboost_forecaster import forecast_spending

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Personal Finance ML API",
    description="AI-powered bank statement analysis with categorization, anomaly detection, and forecasting",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Model directory
MODEL_DIR = Path(__file__).parent.parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

# Static directory
STATIC_DIR = Path(__file__).parent.parent / "static"
IMAGES_DIR = STATIC_DIR / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def create_category_pie_chart(df: pd.DataFrame, base_url: str) -> str:
    """
    Create a pie chart showing spending by category
    
    Args:
        df: DataFrame with categorized transactions
        base_url: Base URL for constructing image links
        
    Returns:
        URL to the saved PNG image
    """
    # Filter expenses
    expenses = df[df['net_amount'] < 0].copy()
    expenses['abs_amount'] = expenses['net_amount'].abs()
    
    # Aggregate by category
    category_spending = expenses.groupby('category')['abs_amount'].sum().sort_values(ascending=False)
    
    # Create pie chart
    fig = go.Figure(data=[go.Pie(
        labels=category_spending.index,
        values=category_spending.values,
        hole=0.3,
        textinfo='label+percent',
        textposition='auto'
    )])
    
    fig.update_layout(
        title="Spending Distribution by Category",
        showlegend=True,
        width=800,
        height=600
    )
    
    # Save to file
    filename = f"pie_{uuid.uuid4()}.png"
    filepath = IMAGES_DIR / filename
    fig.write_image(str(filepath))
    
    return f"{base_url}static/images/{filename}"


def create_anomaly_scatter(df: pd.DataFrame, anomalies_info: dict, base_url: str) -> str:
    """
    Create a scatter plot showing anomalous transactions
    
    Args:
        df: DataFrame with categorized transactions
        anomalies_info: Anomaly detection results
        base_url: Base URL for constructing image links
        
    Returns:
        URL to the saved PNG image
    """
    # Filter expenses
    expenses = df[df['net_amount'] < 0].copy()
    expenses['abs_amount'] = expenses['net_amount'].abs()
    
    # Mark anomalies
    anomaly_dates = [a['date'] for a in anomalies_info['anomaly_transactions']]
    expenses['is_anomaly'] = expenses['date'].dt.strftime('%Y-%m-%d').isin(anomaly_dates)
    
    # Create scatter plot
    fig = go.Figure()
    
    # Normal transactions
    normal = expenses[~expenses['is_anomaly']]
    fig.add_trace(go.Scatter(
        x=normal['date'],
        y=normal['abs_amount'],
        mode='markers',
        name='Normal',
        marker=dict(color='blue', size=6, opacity=0.6)
    ))
    
    # Anomalous transactions
    anomalous = expenses[expenses['is_anomaly']]
    if not anomalous.empty:
        fig.add_trace(go.Scatter(
            x=anomalous['date'],
            y=anomalous['abs_amount'],
            mode='markers',
            name='Anomaly',
            marker=dict(color='red', size=10, symbol='diamond'),
            text=anomalous['desc'],
            hovertemplate='<b>%{text}</b><br>Amount: $%{y:.2f}<br>Date: %{x}<extra></extra>'
        ))
    
    fig.update_layout(
        title="Transaction Anomalies Over Time",
        xaxis_title="Date",
        yaxis_title="Amount ($)",
        showlegend=True,
        width=1000,
        height=600,
        hovermode='closest'
    )
    
    # Save to file
    filename = f"anomaly_{uuid.uuid4()}.png"
    filepath = IMAGES_DIR / filename
    fig.write_image(str(filepath))
    
    return f"{base_url}static/images/{filename}"


def create_forecast_bar(forecast_info: dict, df: pd.DataFrame, base_url: str) -> str:
    """
    Create a bar chart showing forecasted spending
    
    Args:
        forecast_info: Forecast results
        df: Original transaction DataFrame
        base_url: Base URL for constructing image links
        
    Returns:
        URL to the saved PNG image
    """
    # Extract forecasts
    forecasts = forecast_info['forecasts']
    
    if not forecasts:
        # Create empty plot
        fig = go.Figure()
        fig.add_annotation(
            text="Insufficient data for forecasting",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20)
        )
        fig.update_layout(
            title="Spending Forecast (Next 3 Months)",
            width=1000,
            height=600
        )
        # Save to file
        filename = f"forecast_empty_{uuid.uuid4()}.png"
        filepath = IMAGES_DIR / filename
        fig.write_image(str(filepath))
        return f"{base_url}static/images/{filename}"
    
    # Prepare data
    categories = list(forecasts.keys())
    months = ['Month 1', 'Month 2', 'Month 3']
    
    # Create grouped bar chart
    fig = go.Figure()
    
    for i, month in enumerate(months):
        values = [forecasts[cat]['predictions'][i] for cat in categories]
        fig.add_trace(go.Bar(
            name=month,
            x=categories,
            y=values,
            text=[f'${v:.0f}' for v in values],
            textposition='auto'
        ))
    
    fig.update_layout(
        title="Spending Forecast by Category (Next 3 Months)",
        xaxis_title="Category",
        yaxis_title="Forecasted Amount ($)",
        barmode='group',
        showlegend=True,
        width=1000,
        height=600,
        xaxis_tickangle=-45
    )
    
    # Save to file
    filename = f"forecast_{uuid.uuid4()}.png"
    filepath = IMAGES_DIR / filename
    fig.write_image(str(filepath))
    
    return f"{base_url}static/images/{filename}"


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Personal Finance ML API",
        "version": "1.0.0",
        "endpoints": {
            "POST /process-pdf": "Upload and analyze bank statement PDF"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/process-pdf")
async def process_pdf(request: Request, pdf_file: UploadFile = File(...)):
    """
    Process a bank statement PDF and return comprehensive analysis
    
    Args:
        request: FastAPI Request object
        pdf_file: Uploaded PDF file
        
    Returns:
        JSON with categorization, anomalies, forecasts, and visualizations
    """
    temp_pdf_path = None
    
    try:
        base_url = str(request.base_url)
        logger.info(f"Processing uploaded file: {pdf_file.filename}")
        
        # Validate file type
        if not pdf_file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            shutil.copyfileobj(pdf_file.file, temp_file)
            temp_pdf_path = temp_file.name
        
        logger.info("File saved to temporary location")
        
        # Step 1: Extract transactions
        logger.info("Step 1: Extracting transactions from PDF")
        transactions_df = extract_transactions(temp_pdf_path)
        
        if transactions_df.empty:
            raise HTTPException(status_code=400, detail="No transactions found in PDF")
        
        # Step 2: Categorize transactions
        logger.info("Step 2: Categorizing transactions")
        categorized_df, categorization_metrics = categorize_transactions(
            transactions_df,
            batch_size=8
        )
        
        # Step 3: Detect anomalies
        logger.info("Step 3: Detecting anomalies")
        anomalies_info = detect_anomalies(categorized_df)
        
        # Step 4: Generate forecasts
        logger.info("Step 4: Generating spending forecasts")
        try:
            forecast_info = forecast_spending(
                categorized_df,
                n_months=3,
                model_dir=str(MODEL_DIR)
            )
        except ValueError as e:
            logger.warning(f"Forecasting failed: {str(e)}")
            forecast_info = {
                'forecasts': {},
                'training_metrics': {},
                'major_categories': [],
                'avg_mae': 0.0,
                'n_months_ahead': 3
            }
        
        # Step 5: Generate visualizations
        logger.info("Step 5: Generating visualizations")
        
        try:
            category_pie = create_category_pie_chart(categorized_df, base_url)
        except Exception as e:
            logger.error(f"Error creating category pie chart: {str(e)}")
            category_pie = ""
        
        try:
            anomaly_scatter = create_anomaly_scatter(categorized_df, anomalies_info, base_url)
        except Exception as e:
            logger.error(f"Error creating anomaly scatter: {str(e)}")
            anomaly_scatter = ""
        
        try:
            forecast_bar = create_forecast_bar(forecast_info, categorized_df, base_url)
        except Exception as e:
            logger.error(f"Error creating forecast bar: {str(e)}")
            forecast_bar = ""
        
        # Step 6: Prepare summary statistics
        total_transactions = len(transactions_df)
        expenses = categorized_df[categorized_df['net_amount'] < 0]
        total_spend = float(expenses['net_amount'].abs().sum())
        
        date_range = f"{transactions_df['date'].min().year}-{transactions_df['date'].max().year}"
        
        # Prepare top categories with spending amounts
        top_categories = {}
        category_totals = expenses.groupby('category')['net_amount'].apply(lambda x: float(x.abs().sum()))
        for cat, amount in category_totals.nlargest(5).items():
            top_categories[cat] = amount
        
        # Prepare forecast summary
        next_month_forecasts = {}
        if forecast_info['forecasts']:
            for category, forecast_data in forecast_info['forecasts'].items():
                next_month_forecasts[category] = forecast_data['predictions'][0]
        
        # Build response
        response = {
            "summary": {
                "total_transactions": total_transactions,
                "total_spend": total_spend,
                "period": date_range,
                "categories_detected": len(categorization_metrics['categories'])
            },
            "categorization": {
                "categories": categorization_metrics['categories'],
                "avg_confidence": categorization_metrics['avg_confidence'],
                "top_categories": top_categories
            },
            "anomalies": {
                "anomaly_transactions": anomalies_info['anomaly_transactions'][:20],  # Limit to 20
                "anomaly_rate": anomalies_info['anomaly_rate'],
                "largest_anomalies": anomalies_info['largest_anomalies'][:10],  # Top 10
                "total_anomalies": anomalies_info.get('total_anomalies', 0)
            },
            "forecast": {
                "next_month_forecasts": next_month_forecasts,
                "avg_mae": forecast_info['avg_mae'],
                "major_categories": forecast_info['major_categories']
            },
            "plots": {
                "category_pie": category_pie,
                "anomaly_scatter": anomaly_scatter,
                "forecast_bar": forecast_bar
            }
        }
        
        logger.info("Processing complete!")
        
        return JSONResponse(content=response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
    
    finally:
        # Cleanup temporary file
        if temp_pdf_path and Path(temp_pdf_path).exists():
            Path(temp_pdf_path).unlink()
            logger.info("Temporary file cleaned up")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

