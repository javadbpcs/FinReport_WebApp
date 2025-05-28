import time
import pandas_datareader as pdr
from functools import lru_cache
from datetime import datetime, timedelta
import pandas as pd
from typing import Union, Optional, Dict, List

class StockDataFetcher:
    def __init__(self, delay: float = 1.0, max_retries: int = 3):
        """
        Initialize the StockDataFetcher with configurable parameters.
        
        Args:
            delay (float): Delay between API requests in seconds
            max_retries (int): Maximum number of retry attempts for failed requests
        """
        self.delay = delay
        self.max_retries = max_retries
        self.last_request_time = 0
        self.valid_intervals = ['d', 'wk', 'mo', 'm', 'w']  # Valid intervals for Yahoo Finance

    def _validate_interval(self, interval: str) -> str:
        """
        Validate and normalize the interval parameter.
        
        Args:
            interval (str): The interval to validate
            
        Returns:
            str: Normalized interval
            
        Raises:
            ValueError: If interval is invalid
        """
        # Remove any numbers from the interval (e.g., '1d' -> 'd')
        normalized = ''.join(filter(str.isalpha, interval.lower()))
        
        if normalized not in self.valid_intervals:
            raise ValueError(
                f"Invalid interval: {interval}. Valid values are: {', '.join(self.valid_intervals)}"
            )
        return normalized

    def _enforce_rate_limit(self):
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.delay:
            time.sleep(self.delay - time_since_last_request)
        self.last_request_time = time.time()

    @lru_cache(maxsize=100)
    def get_stock_data(
        self,
        ticker: str,
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        interval: str = 'd'
    ) -> Optional[pd.DataFrame]:
        """
        Fetch stock data with error handling and rate limiting.
        
        Args:
            ticker (str): Stock ticker symbol
            start_date (Union[str, datetime]): Start date for data
            end_date (Union[str, datetime]): End date for data
            interval (str): Data interval ('d', 'wk', 'mo')
            
        Returns:
            Optional[pd.DataFrame]: Stock data or None if fetch fails
        """
        # Convert string dates to datetime if necessary
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d')

        # Validate interval
        try:
            interval = self._validate_interval(interval)
        except ValueError as e:
            print(f"Error: {str(e)}")
            return None

        for attempt in range(self.max_retries):
            try:
                self._enforce_rate_limit()
                
                # Fetch the data
                data = pdr.get_data_yahoo(
                    ticker,
                    start=start_date,
                    end=end_date,
                    interval=interval
                )
                
                if data.empty:
                    print(f"No data found for {ticker} between {start_date} and {end_date}")
                    return None
                
                # Add additional calculated columns
                data['Daily_Return'] = data['Close'].pct_change()
                data['Cumulative_Return'] = (1 + data['Daily_Return']).cumprod() - 1
                
                return data
                
            except Exception as e:
                print(f"Attempt {attempt + 1} failed for {ticker}: {str(e)}")
                if attempt == self.max_retries - 1:
                    print(f"Failed to fetch data for {ticker} after {self.max_retries} attempts")
                    return None
                time.sleep(self.delay * 2)  # Exponential backoff

    def get_multiple_stocks(
        self,
        tickers: List[str],
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        interval: str = 'd'
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple stocks.
        
        Args:
            tickers (List[str]): List of stock ticker symbols
            start_date (Union[str, datetime]): Start date for data
            end_date (Union[str, datetime]): End date for data
            interval (str): Data interval ('d', 'wk', 'mo')
            
        Returns:
            Dict[str, pd.DataFrame]: Dictionary of stock dataframes
        """
        results = {}
        for ticker in tickers:
            data = self.get_stock_data(ticker, start_date, end_date, interval)
            if data is not None:
                results[ticker] = data
        return results

def main():
    # Example usage
    fetcher = StockDataFetcher(delay=1.0, max_retries=3)
    
    # Single stock example
    apple_data = fetcher.get_stock_data(
        'AAPL',
        '2023-01-01',
        '2023-12-31',
        'd'  # Changed from '1d' to 'd'
    )
    
    if apple_data is not None:
        print("\nApple Stock Data:")
        print(apple_data.head())
        print("\nSummary Statistics:")
        print(apple_data.describe())
    
    # Multiple stocks example
    tech_stocks = ['MSFT', 'GOOGL', 'AMZN']
    tech_data = fetcher.get_multiple_stocks(
        tech_stocks,
        '2023-01-01',
        '2023-12-31',
        'd'  # Changed from '1d' to 'd'
    )
    
    print("\nTech Stocks Data:")
    for ticker, data in tech_data.items():
        print(f"\n{ticker} - Last Close Price: ${data['Close'].iloc[-1]:.2f}")

if __name__ == "__main__":
    main() 