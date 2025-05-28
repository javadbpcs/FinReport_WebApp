import yfinance as yf
import pandas as pd
from datetime import datetime

def format_revenue(value):
    """
    Format revenue values to millions of dollars.
    
    Args:
        value (float): The revenue value in dollars
        
    Returns:
        str: Formatted revenue in millions of dollars
    """
    if pd.isna(value):
        return "N/A"
    # Convert to millions
    millions = value / 1_000_000
    return f"${millions:,.2f}M"

def get_company_financials(ticker_symbol):
    """
    Fetch comprehensive financial data for a given company ticker symbol.
    
    Args:
        ticker_symbol (str): The stock ticker symbol (e.g., 'AAPL' for Apple)
    
    Returns:
        dict: Dictionary containing various financial metrics
    """
    try:
        # Initialize the company ticker
        company = yf.Ticker(ticker_symbol)
        
        # Get company info
        info = company.info
        
        # Get financial statements
        quarterly_financials = company.quarterly_financials
        annual_financials = company.financials
        quarterly_balance_sheet = company.quarterly_balance_sheet
        annual_balance_sheet = company.balance_sheet
        
        # Get cash flow statements
        quarterly_cash_flow = company.quarterly_cashflow
        annual_cash_flow = company.cashflow
        
        return {
            'company_name': info.get('longName', 'N/A'),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'quarterly_financials': quarterly_financials,
            'annual_financials': annual_financials,
            'quarterly_balance_sheet': quarterly_balance_sheet,
            'annual_balance_sheet': annual_balance_sheet,
            'quarterly_cash_flow': quarterly_cash_flow,
            'annual_cash_flow': annual_cash_flow
        }
    except Exception as e:
        print(f"Error fetching data for {ticker_symbol}: {str(e)}")
        return None

def display_financial_metrics(financial_data):
    """
    Display key financial metrics in a readable format.
    
    Args:
        financial_data (dict): Dictionary containing financial data
    """
    if not financial_data:
        return
    
    print(f"\nCompany: {financial_data['company_name']}")
    print(f"Sector: {financial_data['sector']}")
    print(f"Industry: {financial_data['industry']}")
    
    # Display Quarterly Revenue
    print("\nQuarterly Revenue:")
    if 'Total Revenue' in financial_data['quarterly_financials'].index:
        quarterly_revenue = financial_data['quarterly_financials'].loc['Total Revenue'].head()
        for date, value in quarterly_revenue.items():
            print(f"{date.strftime('%Y-%m-%d')}: {format_revenue(value)}")
    
    # Display Annual Revenue
    print("\nAnnual Revenue:")
    if 'Total Revenue' in financial_data['annual_financials'].index:
        annual_revenue = financial_data['annual_financials'].loc['Total Revenue'].head()
        for date, value in annual_revenue.items():
            print(f"{date.strftime('%Y-%m-%d')}: {format_revenue(value)}")
    
    # Display Quarterly Net Income
    print("\nQuarterly Net Income:")
    if 'Net Income' in financial_data['quarterly_financials'].index:
        quarterly_income = financial_data['quarterly_financials'].loc['Net Income'].head()
        for date, value in quarterly_income.items():
            print(f"{date.strftime('%Y-%m-%d')}: {format_revenue(value)}")
    
    # Display Annual Net Income
    print("\nAnnual Net Income:")
    if 'Net Income' in financial_data['annual_financials'].index:
        annual_income = financial_data['annual_financials'].loc['Net Income'].head()
        for date, value in annual_income.items():
            print(f"{date.strftime('%Y-%m-%d')}: {format_revenue(value)}")

def main():
    # Example usage
    ticker_symbols = ['AAPL', 'MSFT', 'GOOGL']  # Add more tickers as needed
    
    for ticker in ticker_symbols:
        print(f"\n{'='*50}")
        print(f"Fetching data for {ticker}")
        print(f"{'='*50}")
        
        financial_data = get_company_financials(ticker)
        display_financial_metrics(financial_data)

if __name__ == "__main__":
    main() 