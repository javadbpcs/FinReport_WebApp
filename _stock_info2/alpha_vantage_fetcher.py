import time
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.fundamentaldata import FundamentalData
from alpha_vantage.techindicators import TechIndicators
import pandas as pd
from typing import Union, Optional, Dict, List
from datetime import datetime
import os
from dotenv import load_dotenv

class AlphaVantageFetcher:
    def __init__(self, api_key: Optional[str] = None, delay: float = 1.0, max_retries: int = 3):
        """
        Initialize the Alpha Vantage Fetcher.
        
        Args:
            api_key (str, optional): Alpha Vantage API key. If None, will try to load from .env
            delay (float): Delay between API requests in seconds
            max_retries (int): Maximum number of retry attempts for failed requests
        """
        # Load API key from environment if not provided
        if api_key is None:
            load_dotenv()
            api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
            if not api_key:
                raise ValueError("API key not found. Please provide an API key or set ALPHA_VANTAGE_API_KEY in .env file")
        
        self.api_key = api_key
        self.delay = delay
        self.max_retries = max_retries
        self.last_request_time = 0
        
        # Initialize API clients
        self.ts = TimeSeries(key=api_key, output_format='pandas')
        self.fd = FundamentalData(key=api_key, output_format='pandas')
        self.ti = TechIndicators(key=api_key, output_format='pandas')

    def _enforce_rate_limit(self):
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.delay:
            time.sleep(self.delay - time_since_last_request)
        self.last_request_time = time.time()

    def get_time_series(
        self,
        ticker: str,
        interval: str = 'daily',
        output_size: str = 'compact'
    ) -> Optional[pd.DataFrame]:
        """
        Fetch time series data for a stock.
        
        Args:
            ticker (str): Stock ticker symbol
            interval (str): Time interval ('1min', '5min', '15min', '30min', '60min', 'daily', 'weekly', 'monthly')
            output_size (str): Output size ('compact' or 'full')
            
        Returns:
            Optional[pd.DataFrame]: Time series data
        """
        for attempt in range(self.max_retries):
            try:
                self._enforce_rate_limit()
                
                if interval == 'daily':
                    data, _ = self.ts.get_daily(symbol=ticker, outputsize=output_size)
                elif interval == 'weekly':
                    data, _ = self.ts.get_weekly(symbol=ticker)
                elif interval == 'monthly':
                    data, _ = self.ts.get_monthly(symbol=ticker)
                else:
                    data, _ = self.ts.get_intraday(symbol=ticker, interval=interval, outputsize=output_size)
                
                # Add calculated columns
                data['Daily_Return'] = data['4. close'].pct_change()
                data['Cumulative_Return'] = (1 + data['Daily_Return']).cumprod() - 1
                
                return data
                
            except Exception as e:
                print(f"Attempt {attempt + 1} failed for {ticker}: {str(e)}")
                if attempt == self.max_retries - 1:
                    print(f"Failed to fetch time series data for {ticker} after {self.max_retries} attempts")
                    return None
                time.sleep(self.delay * 2)

    def get_fundamental_data(
        self,
        ticker: str,
        report_type: str = 'income'
    ) -> Optional[pd.DataFrame]:
        """
        Fetch fundamental data for a stock.
        
        Args:
            ticker (str): Stock ticker symbol
            report_type (str): Type of report ('income', 'balance', 'cash', 'overview')
            
        Returns:
            Optional[pd.DataFrame]: Fundamental data
        """
        for attempt in range(self.max_retries):
            try:
                self._enforce_rate_limit()
                
                if report_type == 'income':
                    data, _ = self.fd.get_income_statement_annual(symbol=ticker)
                elif report_type == 'balance':
                    data, _ = self.fd.get_balance_sheet_annual(symbol=ticker)
                elif report_type == 'cash':
                    data, _ = self.fd.get_cash_flow_annual(symbol=ticker)
                elif report_type == 'overview':
                    data, _ = self.fd.get_company_overview(symbol=ticker)
                else:
                    raise ValueError(f"Invalid report type: {report_type}")
                
                return data
                
            except Exception as e:
                print(f"Attempt {attempt + 1} failed for {ticker}: {str(e)}")
                if attempt == self.max_retries - 1:
                    print(f"Failed to fetch fundamental data for {ticker} after {self.max_retries} attempts")
                    return None
                time.sleep(self.delay * 2)

    def get_technical_indicators(
        self,
        ticker: str,
        indicator: str = 'SMA',
        interval: str = 'daily',
        time_period: int = 20
    ) -> Optional[pd.DataFrame]:
        """
        Fetch technical indicators for a stock.
        
        Args:
            ticker (str): Stock ticker symbol
            indicator (str): Technical indicator ('SMA', 'EMA', 'RSI', 'MACD', 'BBANDS')
            interval (str): Time interval ('1min', '5min', '15min', '30min', '60min', 'daily', 'weekly', 'monthly')
            time_period (int): Time period for the indicator
            
        Returns:
            Optional[pd.DataFrame]: Technical indicator data
        """
        for attempt in range(self.max_retries):
            try:
                self._enforce_rate_limit()
                
                if indicator == 'SMA':
                    data, _ = self.ti.get_sma(symbol=ticker, interval=interval, time_period=time_period)
                elif indicator == 'EMA':
                    data, _ = self.ti.get_ema(symbol=ticker, interval=interval, time_period=time_period)
                elif indicator == 'RSI':
                    data, _ = self.ti.get_rsi(symbol=ticker, interval=interval, time_period=time_period)
                elif indicator == 'MACD':
                    data, _ = self.ti.get_macd(symbol=ticker, interval=interval)
                elif indicator == 'BBANDS':
                    data, _ = self.ti.get_bbands(symbol=ticker, interval=interval, time_period=time_period)
                else:
                    raise ValueError(f"Invalid indicator: {indicator}")
                
                return data
                
            except Exception as e:
                print(f"Attempt {attempt + 1} failed for {ticker}: {str(e)}")
                if attempt == self.max_retries - 1:
                    print(f"Failed to fetch technical indicators for {ticker} after {self.max_retries} attempts")
                    return None
                time.sleep(self.delay * 2)

def main():
    # Example usage
    fetcher = AlphaVantageFetcher()
    
    # Get time series data
    print("\nFetching daily time series data for AAPL...")
    daily_data = fetcher.get_time_series('AAPL', interval='daily')
    if daily_data is not None:
        print("\nDaily Data:")
        print(daily_data.head())
        
    time.sleep(1)
    # Get fundamental data
    print("\nFetching income statement for AAPL...")
    income_data = fetcher.get_fundamental_data('AAPL', report_type='income')
    if income_data is not None:
        print("\nIncome Statement:")
        print(income_data.head())
        
    time.sleep(1)
    # Get technical indicators
    print("\nFetching SMA for AAPL...")
    sma_data = fetcher.get_technical_indicators('AAPL', indicator='SMA')
    if sma_data is not None:
        print("\nSMA Data:")
        print(sma_data.head())

if __name__ == "__main__":
    main() 