import os
import time
from datetime import datetime, timedelta
from polygon import RESTClient
from dotenv import load_dotenv
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Load environment variables
load_dotenv()

# Initialize Polygon.io client
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')
client = RESTClient(POLYGON_API_KEY)

def format_market_cap(market_cap):
    """
    Format market cap in millions of dollars
    """
    if market_cap is None:
        return "N/A"
    market_cap_millions = market_cap / 1_000_000
    if market_cap_millions >= 1000:
        return f"${market_cap_millions/1000:.2f}B"
    else:
        return f"${market_cap_millions:.2f}M"

def plot_historical_data(ticker: str):
    """
    Plot historical price data for the last year
    """
    try:
        # Get the current date and date 1 year ago
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        # Get daily aggregates
        aggs = client.get_aggs(
            ticker,
            1,
            "day",
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
        time.sleep(2)  # Increased delay between requests
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame([{
            'date': datetime.fromtimestamp(agg.timestamp / 1000),
            'open': agg.open,
            'high': agg.high,
            'low': agg.low,
            'close': agg.close,
            'volume': agg.volume
        } for agg in aggs])
        
        # Calculate moving averages
        df['SMA_20'] = df['close'].rolling(window=20).mean()
        df['SMA_50'] = df['close'].rolling(window=50).mean()
        
        # Create the plot
        plt.figure(figsize=(12, 6))
        plt.plot(df['date'], df['close'], label='Close Price', color='blue')
        plt.plot(df['date'], df['SMA_20'], label='20-day SMA', color='orange')
        plt.plot(df['date'], df['SMA_50'], label='50-day SMA', color='red')
        
        # Customize the plot
        plt.title(f'{ticker} Historical Price Data (Last Year)')
        plt.xlabel('Date')
        plt.ylabel('Price ($)')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()
        
        # Format x-axis dates
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.gca().xaxis.set_major_locator(mdates.MonthLocator())
        plt.xticks(rotation=45)
        
        # Adjust layout and display
        plt.tight_layout()
        plt.show()
        
    except Exception as e:
        print(f"Error plotting historical data: {str(e)}")

def get_stock_fundamentals(ticker: str):
    """
    Get fundamental data for a stock
    """
    try:
        # Get company information
        company_info = client.get_ticker_details(ticker)
        time.sleep(2)  # Increased delay between requests
        
        print(f"\nCompany Information for {ticker}:")
        print("=" * 50)
        
        # Basic Company Information
        print(f"Company Name: {company_info.name}")
        print(f"Market Cap: {format_market_cap(company_info.market_cap)}")
        if hasattr(company_info, 'total_employees'):
            print(f"Total Employees: {company_info.total_employees:,}")
        if hasattr(company_info, 'homepage_url'):
            print(f"Website: {company_info.homepage_url}")
        if hasattr(company_info, 'phone_number'):
            print(f"Phone: {company_info.phone_number}")
        
        # Company Description
        if hasattr(company_info, 'description'):
            print("\nCompany Description:")
            print("-" * 30)
            print(company_info.description)
        
        # Company Address
        if hasattr(company_info, 'address'):
            print("\nCompany Address:")
            print("-" * 30)
            address = company_info.address
            if hasattr(address, 'address1'):
                print(f"Street: {address.address1}")
            if hasattr(address, 'city'):
                print(f"City: {address.city}")
            if hasattr(address, 'state'):
                print(f"State: {address.state}")
            if hasattr(address, 'postal_code'):
                print(f"Postal Code: {address.postal_code}")
        
        # Market Information
        print("\nMarket Information:")
        print("-" * 30)
        if hasattr(company_info, 'primary_exchange'):
            print(f"Primary Exchange: {company_info.primary_exchange}")
        if hasattr(company_info, 'list_date'):
            print(f"List Date: {company_info.list_date}")
        if hasattr(company_info, 'share_class_shares_outstanding'):
            print(f"Shares Outstanding: {company_info.share_class_shares_outstanding:,}")
        if hasattr(company_info, 'weighted_shares_outstanding'):
            print(f"Weighted Shares Outstanding: {company_info.weighted_shares_outstanding:,}")
        
        # Industry Information
        if hasattr(company_info, 'sic_code') or hasattr(company_info, 'sic_description'):
            print("\nIndustry Classification:")
            print("-" * 30)
            if hasattr(company_info, 'sic_code'):
                print(f"SIC Code: {company_info.sic_code}")
            if hasattr(company_info, 'sic_description'):
                print(f"Industry: {company_info.sic_description}")
        
        # Get previous day data
        if hasattr(company_info, 'prev_day'):
            print("\nPrevious Day Trading:")
            print("-" * 30)
            if hasattr(company_info.prev_day, 'close'):
                print(f"Previous Close: ${company_info.prev_day.close:,.2f}")
            if hasattr(company_info.prev_day, 'volume'):
                print(f"Previous Volume: {company_info.prev_day.volume:,}")
        
        # Get financial data using the correct method
        try:
            financials_response = client.vx.list_stock_financials(
                ticker=ticker,
                order="desc",
                limit="1",
                sort="filing_date"
            )
            time.sleep(2)  # Increased delay between requests
            
            if financials_response and hasattr(financials_response, 'results') and financials_response.results:
                latest_financial = financials_response.results[0]
                financial_data = latest_financial.financials
                
                print(f"\nFinancial Data (as of {latest_financial.end_date}):")
                print(f"Fiscal Period: {latest_financial.fiscal_period} {latest_financial.fiscal_year}")
                
                # Income Statement
                if 'income_statement' in financial_data:
                    income_stmt = financial_data['income_statement']
                    print("\nIncome Statement:")
                    print(f"Revenue: ${income_stmt.get('revenues', {}).get('value', 0):,.2f}")
                    print(f"Gross Profit: ${income_stmt.get('gross_profit', {}).get('value', 0):,.2f}")
                    print(f"Operating Income: ${income_stmt.get('operating_income_loss', {}).get('value', 0):,.2f}")
                    print(f"Net Income: ${income_stmt.get('net_income_loss', {}).get('value', 0):,.2f}")
                    print(f"EPS (Basic): ${income_stmt.get('basic_earnings_per_share', {}).get('value', 0):,.2f}")
                    print(f"EPS (Diluted): ${income_stmt.get('diluted_earnings_per_share', {}).get('value', 0):,.2f}")
                
                # Balance Sheet
                if 'balance_sheet' in financial_data:
                    balance_sheet = financial_data['balance_sheet']
                    print("\nBalance Sheet:")
                    print(f"Total Assets: ${balance_sheet.get('assets', {}).get('value', 0):,.2f}")
                    print(f"Current Assets: ${balance_sheet.get('current_assets', {}).get('value', 0):,.2f}")
                    print(f"Total Liabilities: ${balance_sheet.get('liabilities', {}).get('value', 0):,.2f}")
                    print(f"Current Liabilities: ${balance_sheet.get('current_liabilities', {}).get('value', 0):,.2f}")
                    print(f"Total Equity: ${balance_sheet.get('equity', {}).get('value', 0):,.2f}")
                
                # Cash Flow Statement
                if 'cash_flow_statement' in financial_data:
                    cash_flow = financial_data['cash_flow_statement']
                    print("\nCash Flow Statement:")
                    print(f"Operating Cash Flow: ${cash_flow.get('net_cash_flow_from_operating_activities', {}).get('value', 0):,.2f}")
                    print(f"Investing Cash Flow: ${cash_flow.get('net_cash_flow_from_investing_activities', {}).get('value', 0):,.2f}")
                    print(f"Financing Cash Flow: ${cash_flow.get('net_cash_flow_from_financing_activities', {}).get('value', 0):,.2f}")
                    print(f"Net Cash Flow: ${cash_flow.get('net_cash_flow', {}).get('value', 0):,.2f}")
                
        except Exception as e:
            print(f"Warning: Could not fetch detailed financials: {str(e)}")
            
    except Exception as e:
        print(f"Error fetching fundamental data: {str(e)}")

def get_technical_indicators(ticker: str):
    """
    Get technical indicators for a stock
    """
    try:
        # Get the current date and date 30 days ago
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Get daily aggregates
        aggs = client.get_aggs(
            ticker,
            1,
            "day",
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
        time.sleep(2)  # Increased delay between requests
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame([{
            'date': datetime.fromtimestamp(agg.timestamp / 1000),
            'open': agg.open,
            'high': agg.high,
            'low': agg.low,
            'close': agg.close,
            'volume': agg.volume
        } for agg in aggs])
        
        # Calculate technical indicators
        # Simple Moving Averages
        df['SMA_20'] = df['close'].rolling(window=20).mean()
        df['SMA_50'] = df['close'].rolling(window=50).mean()
        
        # Relative Strength Index (RSI)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        print(f"\nTechnical Indicators for {ticker}:")
        print("=" * 50)
        print("\nLatest Technical Indicators:")
        latest = df.iloc[-1]
        print(f"Current Price: ${latest['close']:,.2f}")
        print(f"20-day SMA: ${latest['SMA_20']:,.2f}")
        print(f"50-day SMA: ${latest['SMA_50']:,.2f}")
        
        # RSI Analysis
        rsi_value = latest['RSI']
        print(f"\nRSI (14-day): {rsi_value:.2f}")
        print("\nRSI Interpretation:")
        if rsi_value > 70:
            print("• Overbought condition (RSI > 70)")
            print("• Potential for price correction or reversal")
        elif rsi_value < 30:
            print("• Oversold condition (RSI < 30)")
            print("• Potential for price bounce or reversal")
        else:
            print("• Neutral condition (RSI between 30 and 70)")
            print("• No strong overbought/oversold signals")
        
        print("\nRSI Explanation:")
        print("• RSI measures the speed and change of price movements")
        print("• Values above 70 suggest the stock may be overbought")
        print("• Values below 30 suggest the stock may be oversold")
        print("• 14-day period is the standard timeframe")
        
    except Exception as e:
        print(f"Error fetching technical indicators: {str(e)}")

def main():
    # Example usage
    ticker = "AAPL"  # Apple Inc.
    
    print(f"Analyzing {ticker} stock data...")
    get_stock_fundamentals(ticker)
    get_technical_indicators(ticker)
    plot_historical_data(ticker)

if __name__ == "__main__":
    main() 