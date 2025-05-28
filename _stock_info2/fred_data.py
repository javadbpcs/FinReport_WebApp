import pandas as pd
from fredapi import Fred
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_fred_data(api_key=None, series_id='SP500'):
    """
    Retrieve data from FRED API
    
    Args:
        api_key (str): Your FRED API key. If None, will try to get from environment variable FRED_API_KEY
        series_id (str): The FRED series ID to retrieve (default: S&P 500)
    
    Returns:
        pandas.DataFrame: DataFrame containing the requested data
    """
    # Get API key from environment variable if not provided
    if api_key is None:
        api_key = os.getenv('FRED_API_KEY')
        if api_key is None:
            raise ValueError("FRED API key not found. Please provide it as an argument or set FRED_API_KEY environment variable.")

    # Initialize FRED API client
    fred = Fred(api_key=api_key)
    
    # Get the data
    data = fred.get_series(series_id)
    
    # Convert to DataFrame
    df = pd.DataFrame(data, columns=['Value'])
    df.index.name = 'Date'
    
    return df

if __name__ == "__main__":
    # Example usage
    try:
        # Get S&P 500 data
        sp500_data = get_fred_data(series_id='SP500')
        print("\nS&P 500 Data:")
        print(sp500_data.head())
        
        # Get GDP data
        gdp_data = get_fred_data(series_id='GDP')
        print("\nGDP Data:")
        print(gdp_data.head())
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nTo use this script, you need to:")
        print("1. Get a FRED API key from https://fred.stlouisfed.org/docs/api/api_key.html")
        print("2. Set it as an environment variable: FRED_API_KEY=your_api_key") 