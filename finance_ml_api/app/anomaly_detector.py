"""
Anomaly Detector Module
Detects unusual spending patterns using statistical methods
"""
import pandas as pd
import numpy as np
from scipy import stats
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def detect_anomalies(df: pd.DataFrame, z_threshold: float = 3.0) -> dict:
    """
    Detect anomalous transactions based on Z-score analysis
    
    Args:
        df: DataFrame with categorized transactions
        z_threshold: Z-score threshold for anomaly detection (default: 3.0)
        
    Returns:
        Dictionary containing anomaly information
    """
    try:
        # Filter for expenses only (negative net_amount)
        expenses = df[df['net_amount'] < 0].copy()
        
        if expenses.empty:
            logger.warning("No expense transactions found")
            return {
                'anomaly_transactions': [],
                'anomaly_rate': 0.0,
                'largest_anomalies': [],
                'stats_by_category': {}
            }
        
        # Calculate absolute amounts for analysis
        expenses['abs_amount'] = expenses['net_amount'].abs()
        
        # Group by category and calculate statistics
        category_stats = expenses.groupby('category')['abs_amount'].agg(['mean', 'std', 'count'])
        
        # Calculate Z-scores for each transaction
        expenses['z_score'] = np.nan
        
        for category in expenses['category'].unique():
            mask = expenses['category'] == category
            category_data = expenses.loc[mask, 'abs_amount']
            
            # Get category statistics
            cat_mean = category_stats.loc[category, 'mean']
            cat_std = category_stats.loc[category, 'std']
            cat_count = category_stats.loc[category, 'count']
            
            # Only calculate Z-scores if we have enough data and std > 0
            if cat_count >= 3 and cat_std > 0:
                z_scores = (category_data - cat_mean) / cat_std
                expenses.loc[mask, 'z_score'] = z_scores
            else:
                # Not enough data or no variance - mark as non-anomalous
                expenses.loc[mask, 'z_score'] = 0.0
        
        # Flag anomalies based on absolute Z-score
        expenses['is_anomaly'] = expenses['z_score'].abs() > z_threshold
        
        # Extract anomalies
        anomalies = expenses[expenses['is_anomaly']].copy()
        
        # Calculate anomaly rate
        anomaly_rate = len(anomalies) / len(expenses) if len(expenses) > 0 else 0.0
        
        # Get top anomalies (top 10% or at least top 10)
        n_top = max(10, int(len(anomalies) * 0.1))
        largest_anomalies = anomalies.nlargest(n_top, 'abs_amount')
        
        # Prepare anomaly transactions for output
        anomaly_records = []
        for _, row in anomalies.iterrows():
            anomaly_records.append({
                'date': row['date'].strftime('%Y-%m-%d') if pd.notna(row['date']) else None,
                'description': row['desc'],
                'amount': float(row['abs_amount']),
                'category': row['category'],
                'z_score': float(row['z_score']),
                'expected_range': f"${category_stats.loc[row['category'], 'mean']:.2f} ± ${category_stats.loc[row['category'], 'std']:.2f}"
            })
        
        # Prepare largest anomalies for output
        largest_records = []
        for _, row in largest_anomalies.iterrows():
            largest_records.append({
                'date': row['date'].strftime('%Y-%m-%d') if pd.notna(row['date']) else None,
                'description': row['desc'],
                'amount': float(row['abs_amount']),
                'category': row['category'],
                'z_score': float(row['z_score'])
            })
        
        # Prepare category statistics
        stats_by_category = {}
        for category in category_stats.index:
            stats_by_category[category] = {
                'mean': float(category_stats.loc[category, 'mean']),
                'std': float(category_stats.loc[category, 'std']),
                'count': int(category_stats.loc[category, 'count']),
                'anomaly_count': int(anomalies[anomalies['category'] == category].shape[0])
            }
        
        logger.info(f"Detected {len(anomalies)} anomalies out of {len(expenses)} expenses")
        logger.info(f"Anomaly rate: {anomaly_rate:.2%}")
        
        return {
            'anomaly_transactions': anomaly_records,
            'anomaly_rate': float(anomaly_rate),
            'largest_anomalies': largest_records,
            'stats_by_category': stats_by_category,
            'total_anomalies': len(anomalies),
            'total_expenses': len(expenses)
        }
        
    except Exception as e:
        logger.error(f"Error detecting anomalies: {str(e)}")
        raise


def get_spending_insights(df: pd.DataFrame) -> dict:
    """
    Generate spending insights from transaction data
    
    Args:
        df: DataFrame with categorized transactions
        
    Returns:
        Dictionary containing spending insights
    """
    expenses = df[df['net_amount'] < 0].copy()
    
    if expenses.empty:
        return {
            'total_spending': 0.0,
            'avg_transaction': 0.0,
            'spending_by_category': {},
            'spending_trend': []
        }
    
    expenses['abs_amount'] = expenses['net_amount'].abs()
    
    # Total spending
    total_spending = expenses['abs_amount'].sum()
    
    # Average transaction
    avg_transaction = expenses['abs_amount'].mean()
    
    # Spending by category
    spending_by_category = expenses.groupby('category')['abs_amount'].sum().to_dict()
    
    # Monthly spending trend
    expenses['year_month'] = expenses['date'].dt.to_period('M')
    monthly_spending = expenses.groupby('year_month')['abs_amount'].sum().reset_index()
    monthly_spending['year_month'] = monthly_spending['year_month'].astype(str)
    spending_trend = monthly_spending.to_dict('records')
    
    return {
        'total_spending': float(total_spending),
        'avg_transaction': float(avg_transaction),
        'spending_by_category': {k: float(v) for k, v in spending_by_category.items()},
        'spending_trend': spending_trend
    }

