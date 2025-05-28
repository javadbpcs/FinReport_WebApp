import yfinance as yf
from datetime import datetime
import time
from functools import lru_cache

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
    Cached version of stock info retrieval. Cache_time parameter ensures
    we get fresh data every minute while caching repeated requests.
    """
    try:
        # Create a Ticker object
        stock = yf.Ticker(ticker_symbol)
        
        # Get the latest stock info
        info = stock.info
        
        # Extract relevant information
        stock_data = {
            # Basic Information
            'Symbol': ticker_symbol,
            'Company Name': info.get('longName', 'N/A'),
            'Sector': info.get('sector', 'N/A'),
            'Industry': info.get('industry', 'N/A'),
            'Country': info.get('country', 'N/A'),
            'Website': info.get('website', 'N/A'),
            
            # Company Size and Employees
            'Full Time Employees': f"{info.get('fullTimeEmployees', 'N/A'):,}" if info.get('fullTimeEmployees') not in ['N/A', None] else 'N/A',
            'Market Cap': format_market_cap(info.get('marketCap')),
            
            # Current Trading Information
            'Current Price': format_currency(info.get('currentPrice')),
            'Previous Close': format_currency(info.get('previousClose')),
            'Open': format_currency(info.get('regularMarketOpen')),
            'Day High': format_currency(info.get('dayHigh')),
            'Day Low': format_currency(info.get('dayLow')),
            'Volume': f"{info.get('volume', 'N/A'):,}" if info.get('volume') not in ['N/A', None] else 'N/A',
            
            # 52 Week Information
            '52 Week High': format_currency(info.get('fiftyTwoWeekHigh')),
            '52 Week Low': format_currency(info.get('fiftyTwoWeekLow')),
            
            # Financial Metrics
            'P/E Ratio': format_number(info.get('trailingPE')),
            'Forward P/E': format_number(info.get('forwardPE')),
            'PEG Ratio': format_number(info.get('pegRatio')),
            'Price to Book': format_number(info.get('priceToBook')),
            'Enterprise Value': format_market_cap(info.get('enterpriseValue')),
            
            # Dividend Information
            'Dividend Yield': format_percentage(info.get('dividendYield')),
            'Dividend Rate': format_currency(info.get('dividendRate')),
            'Payout Ratio': format_percentage(info.get('payoutRatio')),
            
            # Growth Metrics
            'Revenue Growth': format_percentage(info.get('revenueGrowth')),
            'Earnings Growth': format_percentage(info.get('earningsGrowth')),
            
            # Trading Metrics
            'Beta': format_number(info.get('beta')),
            'Short Ratio': format_number(info.get('shortRatio')),
            'Profit Margins': format_percentage(info.get('profitMargins')),
            'Operating Margins': format_percentage(info.get('operatingMargins')),
            
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