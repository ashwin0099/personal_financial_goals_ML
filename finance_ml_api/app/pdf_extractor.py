"""
PDF Extractor Module
Extracts transaction data from bank statement PDFs
"""
import camelot
import pandas as pd
import numpy as np
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_transactions(pdf_path: str) -> pd.DataFrame:
    """
    Extract transactions from a bank statement PDF
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        DataFrame with extracted and cleaned transaction data
        
    Raises:
        ValueError: If no tables are found or data is insufficient
    """
    try:
        # Extract tables from PDF using lattice method
        logger.info(f"Extracting tables from {pdf_path}")
        tables = camelot.read_pdf(
            pdf_path, 
            pages='all', 
            flavor='lattice'
        )
        
        if len(tables) == 0:
            raise ValueError("No tables detected in PDF. Please ensure it's a valid bank statement.")
        
        logger.info(f"Found {len(tables)} tables in PDF")
        
        # Concatenate all tables
        dfs = pd.concat([table.df for table in tables], ignore_index=True)
        
        if dfs.empty:
            raise ValueError("Extracted tables are empty")
        
        # Ensure we have at least 5 columns
        if dfs.shape[1] < 5:
            raise ValueError(f"Expected at least 5 columns, found {dfs.shape[1]}")
        
        # Parse transaction date (column 0)
        dfs['transaction_date'] = pd.to_datetime(
            dfs[0], 
            format='%d-%m-%Y', 
            errors='coerce'
        )
        
        # Also try alternative date formats if parsing fails
        if dfs['transaction_date'].isna().all():
            dfs['transaction_date'] = pd.to_datetime(
                dfs[0], 
                format='%d/%m/%Y', 
                errors='coerce'
            )
        if dfs['transaction_date'].isna().all():
            dfs['transaction_date'] = pd.to_datetime(
                dfs[0], 
                errors='coerce'
            )
        
        # Forward fill and backward fill ALL columns
        dfs = dfs.ffill().bfill()
        
        # Convert numeric columns (credited_amount, debited_amount, balance)
        for col in [2, 3, 4]:
            if col < dfs.shape[1]:
                # Remove currency symbols and commas
                dfs[col] = dfs[col].astype(str).str.replace(',', '').str.replace('₹', '').str.strip()
                dfs[col] = pd.to_numeric(dfs[col], errors='coerce')
        
        # Fill NaN in numeric columns with 0
        dfs[[2, 3, 4]] = dfs[[2, 3, 4]].fillna(0)
        
        # Calculate net amount (positive for credits, negative for debits)
        dfs['net_amount'] = dfs[2] - dfs[3]
        
        # Filter valid transactions
        dfs = dfs[
            (dfs['net_amount'].abs() > 0) & 
            (dfs['transaction_date'].notna())
        ].copy()
        
        if dfs.empty:
            raise ValueError("No valid transactions found after filtering")
        
        # Add time-based features
        dfs['month'] = dfs['transaction_date'].dt.month
        dfs['year'] = dfs['transaction_date'].dt.year
        dfs['day_of_week'] = dfs['transaction_date'].dt.dayofweek
        
        # Rename columns for clarity
        dfs = dfs[[
            'transaction_date', 1, 2, 3, 4, 
            'net_amount', 'month', 'year', 'day_of_week'
        ]]
        dfs.columns = [
            'date', 'desc', 'credit', 'debit', 'balance', 
            'net_amount', 'month', 'year', 'day_of_week'
        ]
        
        # Sort by date and reset index
        dfs = dfs.sort_values('date').reset_index(drop=True)
        
        logger.info(f"Successfully extracted {len(dfs)} transactions")
        
        return dfs
        
    except Exception as e:
        logger.error(f"Error extracting transactions: {str(e)}")
        raise


def save_transactions(df: pd.DataFrame, output_path: str) -> None:
    """
    Save transactions DataFrame to parquet format
    
    Args:
        df: Transaction DataFrame
        output_path: Path to save the parquet file
    """
    df.to_parquet(output_path, index=False)
    logger.info(f"Saved transactions to {output_path}")


def load_transactions(input_path: str) -> pd.DataFrame:
    """
    Load transactions from parquet file
    
    Args:
        input_path: Path to the parquet file
        
    Returns:
        Transaction DataFrame
    """
    df = pd.read_parquet(input_path)
    logger.info(f"Loaded {len(df)} transactions from {input_path}")
    return df

