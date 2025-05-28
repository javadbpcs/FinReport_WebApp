import os
import time
from datetime import datetime, timedelta
from polygon import RESTClient
from dotenv import load_dotenv
import pandas as pd
from functools import lru_cache

# Load environment variables
load_dotenv()

# Initialize Polygon.io client
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')
client = RESTClient(POLYGON_API_KEY)

def format_market_cap(market_cap):
    """
    Format market cap to show in Millions, Billions, or Trillions
    
    Args:
        market_cap (float): Market cap value in dollars
    
    Returns:
        str: Formatted market cap with appropriate scale
    """
    if market_cap == 'N/A' or market_cap is None:
        return 'N/A'
    
    try:
        market_cap = float(market_cap)
        if market_cap >= 1e12:  # Trillion
            return f"${market_cap/1e12:.2f}T"
        elif market_cap >= 1e9:  # Billion
            return f"${market_cap/1e9:.2f}B"
        elif market_cap >= 1e6:  # Million
            return f"${market_cap/1e6:.2f}M"
        else:
            return f"${market_cap:,.2f}"
    except (ValueError, TypeError):
        return 'N/A'

def format_currency(value):
    """
    Format value with dollar sign and commas
    
    Args:
        value: The value to format
    
    Returns:
        str: Formatted value with dollar sign
    """
    if value == 'N/A' or value is None:
        return 'N/A'
    try:
        return f"${float(value):,.2f}"
    except (ValueError, TypeError):
        return 'N/A'

def format_percentage(value):
    """
    Format value as percentage
    
    Args:
        value: The value to format
    
    Returns:
        str: Formatted percentage
    """
    if value == 'N/A' or value is None:
        return 'N/A'
    try:
        return f"{float(value) * 100:.2f}%"
    except (ValueError, TypeError):
        return 'N/A'

def format_number(value, decimals=2):
    """
    Format number with specified decimal places
    
    Args:
        value: The value to format
        decimals: Number of decimal places
    
    Returns:
        str: Formatted number
    """
    if value == 'N/A' or value is None:
        return 'N/A'
    try:
        return f"{float(value):.{decimals}f}"
    except (ValueError, TypeError):
        return 'N/A'

@lru_cache(maxsize=100)
def get_cached_stock_info(ticker_symbol: str, cache_time: int):
    """
    Cached version of stock info retrieval using Polygon.io. Cache_time parameter ensures
    we get fresh data every minute while caching repeated requests.
    """
    try:
        # Get company information
        company_info = client.get_ticker_details(ticker_symbol)
        time.sleep(2)  # Increased delay between requests
        
        # Get previous day data
        prev_day = company_info.prev_day if hasattr(company_info, 'prev_day') else None
        
        # Get technical indicators
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Get daily aggregates for technical analysis
        aggs = client.get_aggs(
            ticker_symbol,
            1,
            "day",
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
        time.sleep(2)  # Increased delay between requests
        
        # Convert to DataFrame for technical analysis
        df = pd.DataFrame([{
            'date': datetime.fromtimestamp(agg.timestamp / 1000),
            'open': agg.open,
            'high': agg.high,
            'low': agg.low,
            'close': agg.close,
            'volume': agg.volume
        } for agg in aggs])
        
        # Calculate technical indicators
        df['SMA_20'] = df['close'].rolling(window=20).mean()
        df['SMA_50'] = df['close'].rolling(window=50).mean()
        
        # Calculate RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Get latest values
        latest = df.iloc[-1]
        
        # Extract relevant information
        stock_data = {
            # Basic Information
            'Symbol': ticker_symbol,
            'Company Name': company_info.name,
            'Sector': getattr(company_info, 'sector', 'N/A'),
            'Industry': getattr(company_info, 'sic_description', 'N/A'),
            'Country': getattr(company_info, 'country', 'N/A'),
            'Website': getattr(company_info, 'homepage_url', 'N/A'),
            
            # Company Size and Employees
            'Full Time Employees': f"{getattr(company_info, 'total_employees', 'N/A'):,}" if hasattr(company_info, 'total_employees') else 'N/A',
            'Market Cap': format_market_cap(getattr(company_info, 'market_cap', None)),
            
            # Current Trading Information
            'Current Price': format_currency(latest['close']),
            'Previous Close': format_currency(prev_day.close if prev_day else None),
            'Open': format_currency(latest['open']),
            'Day High': format_currency(latest['high']),
            'Day Low': format_currency(latest['low']),
            'Volume': f"{latest['volume']:,}",
            
            # Technical Indicators
            '20-day SMA': format_currency(latest['SMA_20']),
            '50-day SMA': format_currency(latest['SMA_50']),
            'RSI': format_number(latest['RSI']),
            
            # Market Information
            'Primary Exchange': getattr(company_info, 'primary_exchange', 'N/A'),
            'List Date': getattr(company_info, 'list_date', 'N/A'),
            'Shares Outstanding': f"{getattr(company_info, 'share_class_shares_outstanding', 'N/A'):,}" if hasattr(company_info, 'share_class_shares_outstanding') else 'N/A',
            
            # Additional Information
            'Last Updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return stock_data
    
    except Exception as e:
        return {'error': f'Error fetching data for {ticker_symbol}: {str(e)}'}

def get_stock_info(ticker_symbol):
    """
    Get the latest information about a stock using its ticker symbol.
    Uses caching to prevent rate limiting.
    
    Args:
        ticker_symbol (str): The stock ticker symbol (e.g., 'AAPL' for Apple)
    
    Returns:
        dict: A dictionary containing the stock information
    """
    # Use current minute as cache key to ensure fresh data every minute
    cache_time = int(time.time() / 60)
    return get_cached_stock_info(ticker_symbol, cache_time)

def main():
    # Example usage
    while True:
        ticker = input("\nEnter stock ticker symbol (or 'quit' to exit): ").upper()
        
        if ticker.lower() == 'quit':
            break
            
        result = get_stock_info(ticker)
        
        if 'error' in result:
            print(result['error'])
        else:
            print("\nStock Information:")
            print("-" * 50)
            for key, value in result.items():
                print(f"{key}: {value}")

if __name__ == "__main__":
    main() 