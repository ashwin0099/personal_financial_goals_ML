"""
Test Script for Personal Finance ML API
Run this script to test the API with a sample PDF
"""
import requests
import json
import sys
from pathlib import Path


def test_api(pdf_path: str, api_url: str = "http://localhost:8000"):
    """
    Test the API with a PDF file
    
    Args:
        pdf_path: Path to the PDF file
        api_url: API base URL
    """
    # Check if file exists
    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    # Check if API is running
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code != 200:
            print(f"Error: API health check failed")
            sys.exit(1)
        print("✓ API is running")
    except requests.exceptions.RequestException as e:
        print(f"Error: Cannot connect to API at {api_url}")
        print(f"Make sure the API is running with: uvicorn app.main:app --host 0.0.0.0 --port 8000")
        sys.exit(1)
    
    # Upload PDF
    print(f"\nUploading PDF: {pdf_path}")
    
    with open(pdf_path, 'rb') as f:
        files = {'pdf_file': f}
        
        try:
            response = requests.post(
                f"{api_url}/process-pdf",
                files=files,
                timeout=120  # 2 minutes timeout
            )
            
            if response.status_code == 200:
                print("✓ PDF processed successfully!\n")
                
                result = response.json()
                
                # Print summary
                print("=" * 60)
                print("SUMMARY")
                print("=" * 60)
                print(f"Total Transactions: {result['summary']['total_transactions']}")
                print(f"Total Spend: ${result['summary']['total_spend']:.2f}")
                print(f"Period: {result['summary']['period']}")
                print(f"Categories Detected: {result['summary']['categories_detected']}")
                
                # Print categorization
                print("\n" + "=" * 60)
                print("CATEGORIZATION")
                print("=" * 60)
                print(f"Average Confidence: {result['categorization']['avg_confidence']:.2%}")
                print("\nTop Categories by Spending:")
                for category, amount in list(result['categorization']['top_categories'].items())[:5]:
                    print(f"  {category}: ${amount:.2f}")
                
                # Print anomalies
                print("\n" + "=" * 60)
                print("ANOMALIES")
                print("=" * 60)
                print(f"Anomaly Rate: {result['anomalies']['anomaly_rate']:.2%}")
                print(f"Total Anomalies: {result['anomalies']['total_anomalies']}")
                
                if result['anomalies']['largest_anomalies']:
                    print("\nTop 5 Largest Anomalies:")
                    for i, anomaly in enumerate(result['anomalies']['largest_anomalies'][:5], 1):
                        print(f"  {i}. ${anomaly['amount']:.2f} - {anomaly['description'][:50]}")
                        print(f"     Date: {anomaly['date']}, Z-score: {anomaly['z_score']:.2f}")
                
                # Print forecast
                print("\n" + "=" * 60)
                print("FORECAST (Next Month)")
                print("=" * 60)
                if result['forecast']['next_month_forecasts']:
                    print(f"Average MAE: ${result['forecast']['avg_mae']:.2f}")
                    print("\nPredicted Spending by Category:")
                    for category, amount in result['forecast']['next_month_forecasts'].items():
                        print(f"  {category}: ${amount:.2f}")
                else:
                    print("Insufficient data for forecasting (need 6+ months)")
                
                # Print visualization info
                print("\n" + "=" * 60)
                print("VISUALIZATIONS")
                print("=" * 60)
                if result['plots']['category_pie']:
                    print("✓ Category Pie Chart generated")
                if result['plots']['anomaly_scatter']:
                    print("✓ Anomaly Scatter Plot generated")
                if result['plots']['forecast_bar']:
                    print("✓ Forecast Bar Chart generated")
                
                # Save full response
                output_file = "api_response.json"
                with open(output_file, 'w') as f:
                    json.dump(result, f, indent=2)
                print(f"\n✓ Full response saved to: {output_file}")
                
                # Save plots
                if result['plots']['category_pie']:
                    save_base64_image(result['plots']['category_pie'], "category_pie.png")
                if result['plots']['anomaly_scatter']:
                    save_base64_image(result['plots']['anomaly_scatter'], "anomaly_scatter.png")
                if result['plots']['forecast_bar']:
                    save_base64_image(result['plots']['forecast_bar'], "forecast_bar.png")
                
                print("\n" + "=" * 60)
                
            else:
                print(f"Error: API returned status code {response.status_code}")
                print(f"Response: {response.text}")
                
        except requests.exceptions.Timeout:
            print("Error: Request timed out. The PDF might be too large or complex.")
        except Exception as e:
            print(f"Error: {str(e)}")


def save_base64_image(base64_string: str, filename: str):
    """Save a base64 encoded image to file"""
    import base64
    
    # Remove the data:image/png;base64, prefix
    image_data = base64_string.split(',')[1] if ',' in base64_string else base64_string
    
    # Decode and save
    with open(filename, 'wb') as f:
        f.write(base64.b64decode(image_data))
    
    print(f"✓ Saved plot: {filename}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_api.py <path_to_pdf>")
        print("Example: python test_api.py sample_statement.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    test_api(pdf_path)

