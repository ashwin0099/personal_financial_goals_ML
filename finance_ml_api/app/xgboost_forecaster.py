"""
XGBoost Forecaster Module
Forecasts future spending using XGBoost regression models
"""
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error
import joblib
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SpendingForecaster:
    """XGBoost-based forecasting for spending predictions"""
    
    def __init__(self, min_history_months: int = 6):
        """
        Initialize the forecaster
        
        Args:
            min_history_months: Minimum months of history required for forecasting
        """
        self.min_history_months = min_history_months
        self.models = {}
        self.feature_columns = []
        self.major_categories = []
    
    def _create_monthly_features(self, monthly_df: pd.DataFrame) -> pd.DataFrame:
        """
        Create time-series features for monthly data
        
        Args:
            monthly_df: DataFrame with monthly aggregated data
            
        Returns:
            DataFrame with engineered features
        """
        df = monthly_df.copy()
        
        # Lag features
        df['lag_1'] = df['amount'].shift(1)
        df['lag_2'] = df['amount'].shift(2)
        df['lag_3'] = df['amount'].shift(3)
        
        # Rolling statistics
        df['rolling_3m'] = df['amount'].rolling(window=3, min_periods=1).mean()
        df['rolling_std_3m'] = df['amount'].rolling(window=3, min_periods=1).std()
        
        # Seasonal features
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
        
        # Trend features
        df['total_trend'] = df['amount'].pct_change()
        df['month_index'] = range(len(df))
        
        # Fill NaN values
        df = df.ffill().fillna(0)
        
        return df
    
    def _prepare_data(self, df: pd.DataFrame) -> dict:
        """
        Prepare monthly aggregated data by category
        
        Args:
            df: Transaction DataFrame with categories
            
        Returns:
            Dictionary of category -> monthly DataFrame
        """
        # Filter expenses
        expenses = df[df['net_amount'] < 0].copy()
        expenses['abs_amount'] = expenses['net_amount'].abs()
        
        # Create year-month column
        expenses['year_month'] = expenses['date'].dt.to_period('M')
        
        # Aggregate by category and month
        monthly_by_category = expenses.groupby(
            ['year_month', 'category']
        )['abs_amount'].sum().reset_index()
        
        # Calculate total spending to identify major categories (>5%)
        total_spending = expenses['abs_amount'].sum()
        category_spending = expenses.groupby('category')['abs_amount'].sum()
        major_categories = category_spending[category_spending / total_spending > 0.05].index.tolist()
        
        self.major_categories = major_categories
        logger.info(f"Major categories (>5% spending): {major_categories}")
        
        # Prepare data for each major category
        category_data = {}
        
        for category in major_categories:
            cat_data = monthly_by_category[monthly_by_category['category'] == category].copy()
            
            if len(cat_data) < self.min_history_months:
                logger.warning(f"Category '{category}' has insufficient history ({len(cat_data)} months)")
                continue
            
            # Extract features
            cat_data['month'] = cat_data['year_month'].dt.month
            cat_data['year'] = cat_data['year_month'].dt.year
            cat_data = cat_data.rename(columns={'abs_amount': 'amount'})
            cat_data = cat_data.sort_values('year_month').reset_index(drop=True)
            
            # Create features
            cat_data = self._create_monthly_features(cat_data)
            
            category_data[category] = cat_data
        
        return category_data
    
    def train_models(self, df: pd.DataFrame) -> dict:
        """
        Train XGBoost models for each major category
        
        Args:
            df: Transaction DataFrame with categories
            
        Returns:
            Dictionary with training metrics
        """
        # Prepare data
        category_data = self._prepare_data(df)
        
        if not category_data:
            raise ValueError("Insufficient data for forecasting. Need at least 6 months of history.")
        
        # Feature columns
        self.feature_columns = [
            'lag_1', 'lag_2', 'lag_3', 
            'rolling_3m', 'rolling_std_3m',
            'month_sin', 'month_cos',
            'total_trend', 'month_index'
        ]
        
        metrics = {}
        
        for category, cat_df in category_data.items():
            logger.info(f"Training model for category: {category}")
            
            # Prepare features and target
            X = cat_df[self.feature_columns]
            y = cat_df['amount']
            
            # Time series split
            tscv = TimeSeriesSplit(n_splits=min(5, len(X) - 1))
            
            # Train model
            model = xgb.XGBRegressor(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                random_state=42,
                objective='reg:squarederror'
            )
            
            # Cross-validation
            mae_scores = []
            for train_idx, test_idx in tscv.split(X):
                X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
                y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
                
                model.fit(X_train, y_train, verbose=False)
                y_pred = model.predict(X_test)
                mae = mean_absolute_error(y_test, y_pred)
                mae_scores.append(mae)
            
            avg_mae = np.mean(mae_scores)
            
            # Train final model on all data
            model.fit(X, y, verbose=False)
            
            # Store model
            self.models[category] = {
                'model': model,
                'last_data': cat_df.iloc[-1].to_dict(),
                'mae': avg_mae
            }
            
            metrics[category] = {
                'mae': float(avg_mae),
                'cv_maes': [float(m) for m in mae_scores],
                'data_points': len(cat_df)
            }
            
            logger.info(f"Category '{category}' - MAE: {avg_mae:.2f}")
        
        return metrics
    
    def forecast(self, n_months: int = 3) -> dict:
        """
        Forecast spending for next N months
        
        Args:
            n_months: Number of months to forecast
            
        Returns:
            Dictionary with forecasts by category
        """
        if not self.models:
            raise ValueError("No trained models available. Run train_models first.")
        
        forecasts = {}
        
        for category, model_data in self.models.items():
            model = model_data['model']
            last_data = model_data['last_data']
            
            predictions = []
            current_features = {k: last_data[k] for k in self.feature_columns}
            
            # Recursive forecasting
            for i in range(n_months):
                # Prepare feature vector
                X_pred = pd.DataFrame([current_features])
                
                # Predict
                pred = model.predict(X_pred)[0]
                predictions.append(max(0, pred))  # Ensure non-negative
                
                # Update features for next prediction
                current_features['lag_3'] = current_features['lag_2']
                current_features['lag_2'] = current_features['lag_1']
                current_features['lag_1'] = pred
                current_features['rolling_3m'] = np.mean([
                    current_features['lag_1'],
                    current_features['lag_2'],
                    current_features['lag_3']
                ])
                current_features['month_index'] += 1
                
                # Update seasonal features
                next_month = (last_data['month'] + i + 1) % 12
                if next_month == 0:
                    next_month = 12
                current_features['month_sin'] = np.sin(2 * np.pi * next_month / 12)
                current_features['month_cos'] = np.cos(2 * np.pi * next_month / 12)
            
            forecasts[category] = {
                'predictions': [float(p) for p in predictions],
                'mae': float(model_data['mae'])
            }
        
        logger.info(f"Generated forecasts for {len(forecasts)} categories")
        
        return forecasts
    
    def save(self, model_dir: str):
        """
        Save trained models
        
        Args:
            model_dir: Directory to save models
        """
        model_path = Path(model_dir)
        model_path.mkdir(parents=True, exist_ok=True)
        
        for category, model_data in self.models.items():
            # Clean category name for filename
            clean_category = category.replace('_', '').replace(' ', '')
            filepath = model_path / f"xgb_{clean_category}.pkl"
            joblib.dump(model_data, filepath)
            logger.info(f"Saved model for '{category}' to {filepath}")
        
        # Save forecaster config
        config = {
            'feature_columns': self.feature_columns,
            'major_categories': self.major_categories,
            'min_history_months': self.min_history_months
        }
        config_path = model_path / "forecaster_config.pkl"
        joblib.dump(config, config_path)
        logger.info(f"Saved forecaster config to {config_path}")
    
    @classmethod
    def load(cls, model_dir: str):
        """
        Load trained models
        
        Args:
            model_dir: Directory containing saved models
            
        Returns:
            SpendingForecaster instance with loaded models
        """
        model_path = Path(model_dir)
        
        # Load config
        config_path = model_path / "forecaster_config.pkl"
        if not config_path.exists():
            raise FileNotFoundError(f"Config not found at {config_path}")
        
        config = joblib.load(config_path)
        
        # Create forecaster instance
        forecaster = cls(min_history_months=config['min_history_months'])
        forecaster.feature_columns = config['feature_columns']
        forecaster.major_categories = config['major_categories']
        
        # Load models
        for category in forecaster.major_categories:
            clean_category = category.replace('_', '').replace(' ', '')
            filepath = model_path / f"xgb_{clean_category}.pkl"
            
            if filepath.exists():
                forecaster.models[category] = joblib.load(filepath)
                logger.info(f"Loaded model for '{category}'")
        
        return forecaster


def forecast_spending(df: pd.DataFrame, n_months: int = 3, model_dir: str = None) -> dict:
    """
    Train and forecast spending for next N months
    
    Args:
        df: Transaction DataFrame with categories
        n_months: Number of months to forecast
        model_dir: Directory to save/load models
        
    Returns:
        Dictionary with forecasts and metrics
    """
    # Create forecaster
    forecaster = SpendingForecaster()
    
    # Train models
    training_metrics = forecaster.train_models(df)
    
    # Generate forecasts
    forecasts = forecaster.forecast(n_months)
    
    # Save models if directory provided
    if model_dir:
        forecaster.save(model_dir)
    
    # Calculate overall metrics
    avg_mae = np.mean([m['mae'] for m in training_metrics.values()])
    
    return {
        'forecasts': forecasts,
        'training_metrics': training_metrics,
        'major_categories': forecaster.major_categories,
        'avg_mae': float(avg_mae),
        'n_months_ahead': n_months
    }

