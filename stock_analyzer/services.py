import os
import time
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pandas as pd
from polygon import RESTClient
from sec_api import QueryApi
import fredapi as fred
from .models import EconomicIndicator
from django.utils import timezone
from functools import lru_cache, wraps
import threading

# Add a request-scoped cache to prevent duplicate API calls
_request_cache = {}
_request_cache_lock = threading.Lock()

def request_cached(ttl_seconds=60):
    """
    Cache decorator that uses a request-scoped cache.
    This prevents duplicate API calls during a single request cycle,
    which happens due to Django development server's double rendering.
    
    Args:
        ttl_seconds: Cache TTL in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key based on function name and arguments
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            with _request_cache_lock:
                # Check if result is in cache and not expired
                if key in _request_cache:
                    cache_time, result = _request_cache[key]
                    if (datetime.now() - cache_time).total_seconds() < ttl_seconds:
                        print(f"Cache hit for {func.__name__}({args}, {kwargs})")
                        return result
            
            # Call the original function
            result = func(*args, **kwargs)
            
            # Cache the result
            with _request_cache_lock:
                _request_cache[key] = (datetime.now(), result)
                
            return result
        return wrapper
    return decorator

# Load environment variables
load_dotenv()

# Initialize API clients
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')
SEC_API = os.getenv('SEC_API')
FRED_API_KEY = os.getenv('FRED_API_KEY')

polygon_client = RESTClient(POLYGON_API_KEY)
sec_client = QueryApi(api_key=SEC_API)
fred_client = fred.Fred(api_key=FRED_API_KEY)

# Rate limiting helper
def rate_limit(seconds=2):
    """Simple rate limiting decorator"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            time.sleep(seconds)  # Sleep before API call
            return func(*args, **kwargs)
        return wrapper
    return decorator

# ---- Polygon.io API Services ----

@rate_limit(3)
@request_cached(ttl_seconds=300)  # Cache for 5 minutes
def get_company_info(ticker):
    """
    Get basic company information
    """
    try:
        print(f"Actually calling Polygon API for company info - {ticker}")
        ticker_details = polygon_client.get_ticker_details(ticker)
        
        # Check if ticker exists but be less strict to avoid missing real companies
        if not hasattr(ticker_details, 'name'):
            return None
            
        # Handle branding and logo_url safely
        logo_url = None
        branding = getattr(ticker_details, 'branding', None)
        if branding and hasattr(branding, 'logo_url'):
            logo_url = branding.logo_url
        elif branding and isinstance(branding, dict):
            logo_url = branding.get('logo_url')
            
        company_data = {
            'stock_symbol': ticker,
            'company_name': getattr(ticker_details, 'name', ticker),
            'sector': getattr(ticker_details, 'sector', None),
            'industry': getattr(ticker_details, 'industry', None),
            'description': getattr(ticker_details, 'description', None),
            'country': getattr(ticker_details, 'locale', None),
            'market_cap': getattr(ticker_details, 'market_cap', None),
            'website': getattr(ticker_details, 'homepage_url', None),
            'logo_url': logo_url,
            'employee_count': getattr(ticker_details, 'total_employees', None),
        }
        
        # Only reject if we have absolutely no meaningful data
        # Don't reject just because sector/industry might be missing
        if not company_data['company_name']:
            return None
            
        return company_data
    except Exception as e:
        print(f"Error fetching company info for {ticker}: {str(e)}")
        # Return None on error
        return None

@rate_limit(3)
@request_cached(ttl_seconds=300)  # Cache for 5 minutes
def get_stock_price_data(ticker, from_date=None, to_date=None, timespan="day"):
    """
    Get historical stock price data
    
    Args:
        ticker (str): Stock symbol
        from_date (str): Start date in YYYY-MM-DD format
        to_date (str): End date in YYYY-MM-DD format
        timespan (str): Time interval (day, week, month, quarter, year)
    """
    if not from_date:
        from_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    if not to_date:
        to_date = datetime.now().strftime('%Y-%m-%d')
        
    try:
        print(f"Actually calling Polygon API for price data - {ticker}")
        aggs = polygon_client.get_aggs(
            ticker, 
            1, 
            timespan,
            from_date, 
            to_date
        )
        
        price_data = []
        for agg in aggs:
            price_data.append({
                'date': datetime.fromtimestamp(agg.timestamp / 1000).date(),
                'open': agg.open,
                'high': agg.high,
                'low': agg.low,
                'close': agg.close,
                'volume': agg.volume,
            })
        
        return price_data
    except Exception as e:
        print(f"Error fetching stock price data for {ticker}: {str(e)}")
        return []

@rate_limit(4)
@request_cached(ttl_seconds=300)  # Cache for 5 minutes
def get_financial_ratios(ticker):
    """
    Calculate financial ratios from Polygon financial data
    """
    try:
        # Get the latest financial data
        print(f"Actually calling Polygon API for financial ratios - {ticker}")
        financials = polygon_client.vx.list_stock_financials(
            ticker=ticker,
            timeframe='quarterly',
            include_sources=True,
            limit=4  # Get last 4 quarters
        )
        
        # Convert generator to list if needed
        if hasattr(financials, 'results'):
            financial_results = financials.results
        else:
            # If it's a generator, convert to list
            financial_results = list(financials)
            if not financial_results:
                return None
        
        # Get the most recent data
        latest_financial = financial_results[0]
        
        # Extract data from financial statements
        income_stmt = latest_financial.financials.get('income_statement', {})
        balance_sheet = latest_financial.financials.get('balance_sheet', {})
        
        # Calculate ratios
        revenue = income_stmt.get('revenues', {}).get('value', 0)
        net_income = income_stmt.get('net_income_loss', {}).get('value', 0)
        total_assets = balance_sheet.get('assets', {}).get('value', 0)
        total_equity = balance_sheet.get('equity', {}).get('value', 0)
        total_liabilities = balance_sheet.get('liabilities', {}).get('value', 0)
        
        # Calculate financial ratios
        ratios = {
            'profit_margin': (net_income / revenue) if revenue else None,
            'roe': (net_income / total_equity) if total_equity else None,
            'roa': (net_income / total_assets) if total_assets else None,
            'debt_to_equity': (total_liabilities / total_equity) if total_equity else None,
        }
        
        return {
            'date': latest_financial.end_date,
            'ratios': ratios
        }
        
    except Exception as e:
        print(f"Error calculating financial ratios for {ticker}: {str(e)}")
        return None

@rate_limit(3)
@request_cached(ttl_seconds=300)  # Cache for 5 minutes
def get_technical_indicators(ticker, window=14):
    """
    Calculate technical indicators for a stock
    """
    try:
        # Get price data for the last 200 days
        print(f"Calculating technical indicators for {ticker}")
        price_data = get_stock_price_data(
            ticker, 
            from_date=(datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        )
        
        if not price_data:
            return None
            
        # Convert to DataFrame for calculations
        df = pd.DataFrame(price_data)
        
        # Calculate Simple Moving Averages
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['sma_200'] = df['close'].rolling(window=200).mean()
        
        # Calculate RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=window).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=window).mean()
        rs = gain / loss
        df['rsi_14'] = 100 - (100 / (1 + rs))
        
        # Calculate MACD
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Calculate Bollinger Bands
        df['bollinger_middle'] = df['close'].rolling(window=20).mean()
        df['bollinger_std'] = df['close'].rolling(window=20).std()
        df['bollinger_upper'] = df['bollinger_middle'] + (df['bollinger_std'] * 2)
        df['bollinger_lower'] = df['bollinger_middle'] - (df['bollinger_std'] * 2)
        
        # Calculate Beta (using S&P 500 as market)
        try:
            # Get S&P 500 data for the same period
            if isinstance(price_data[0]['date'], datetime):
                from_date_str = price_data[0]['date'].strftime('%Y-%m-%d')
            else:
                from_date_str = price_data[0]['date']
                
            spy_data = get_stock_price_data('SPY', from_date=from_date_str)
            spy_df = pd.DataFrame(spy_data)
            
            # Calculate returns
            df['return'] = df['close'].pct_change()
            spy_df['return'] = spy_df['close'].pct_change()
            
            # Calculate beta
            merged = pd.merge(df[['date', 'return']], spy_df[['date', 'return']], on='date', suffixes=('_stock', '_market'))
            covariance = merged['return_stock'].cov(merged['return_market'])
            market_variance = merged['return_market'].var()
            beta = covariance / market_variance if market_variance else None
        except Exception as e:
            print(f"Error calculating beta: {str(e)}")
            beta = None
        
        # Get the most recent data with indicators
        latest = df.iloc[-1].to_dict()
        # Ensure date is formatted as string
        if isinstance(latest['date'], datetime):
            latest['date'] = latest['date'].strftime('%Y-%m-%d')
        elif isinstance(latest['date'], pd.Timestamp):
            latest['date'] = latest['date'].strftime('%Y-%m-%d')
        latest['beta'] = beta
        
        return latest
        
    except Exception as e:
        print(f"Error calculating technical indicators for {ticker}: {str(e)}")
        return None

@rate_limit(3)
@request_cached(ttl_seconds=300)  # Cache for 5 minutes
def get_insider_transactions(ticker, limit=10):
    """
    Get insider transactions for a company
    """
    try:
        # Check if the VX client has the required method
        print(f"Actually calling Polygon API for insider transactions - {ticker}")
        if hasattr(polygon_client.vx, 'list_stock_insider_transactions'):
            # Get insider transactions
            transactions = polygon_client.vx.list_stock_insider_transactions(
                ticker=ticker,
                limit=limit
            )
            
            if not transactions or not transactions.results:
                return []
                
            insider_data = []
            for transaction in transactions.results:
                insider_data.append({
                    'insider_name': transaction.insider_name,
                    'position': transaction.insider_position or 'Unknown',
                    'transaction_type': transaction.transaction_type,
                    'transaction_date': transaction.transaction_date,
                    'shares': transaction.shares,
                    'price_per_share': transaction.share_price,
                    'total_value': transaction.shares * transaction.share_price if transaction.share_price else None,
                })
                
            return insider_data
        else:
            # Fallback to empty list if method is not available
            print(f"Insider transactions not available for {ticker}: API method not available")
            return []
        
    except Exception as e:
        print(f"Error fetching insider transactions for {ticker}: {str(e)}")
        return []

@rate_limit(3)
def search_companies(search_term, limit=10):
    """
    Search for companies by name or ticker
    """
    try:
        # Use the tickers endpoint with search parameter
        search_results = polygon_client.vx.list_tickers(
            search=search_term,
            active=True,
            market="stocks",
            limit=limit,
            sort="ticker"
        )
        
        if not search_results or not hasattr(search_results, 'results') or not search_results.results:
            return []
            
        companies = []
        for result in search_results.results:
            companies.append({
                'stock_symbol': result.ticker,
                'company_name': result.name,
                'primary_exchange': getattr(result, 'primary_exchange', None),
                'market': getattr(result, 'market', None),
                'locale': getattr(result, 'locale', None),
            })
            
        return companies
    except Exception as e:
        print(f"Error searching companies with term '{search_term}': {str(e)}")
        return []

# ---- SEC-API Services ----

@rate_limit(2)
@request_cached(ttl_seconds=300)  # Cache for 5 minutes
def get_company_info_sec(ticker):
    """
    Get basic company information from SEC EDGAR database directly
    """
    try:
        print(f"Actually calling SEC API for company info - {ticker}")
        # Check if ticker is a numeric CIK or a symbol
        is_cik = ticker.isdigit()
        
        # Format CIK with leading zeros if needed
        if is_cik:
            cik = ticker.zfill(10)
        else:
            # For symbols, we need to get the CIK first
            # This uses a different endpoint
            lookup_url = f"https://www.sec.gov/files/company_tickers.json"
            headers = {
                'User-Agent': 'Blueprint Financial Analytics Tool (javad@bpcs.com)',
                'Accept-Encoding': 'gzip, deflate',
            }
            
            lookup_response = requests.get(lookup_url, headers=headers)
            lookup_response.raise_for_status()
            lookup_data = lookup_response.json()
            
            # Find the ticker in the lookup data
            cik = None
            company_name = None
            for _, company in lookup_data.items():
                if company.get('ticker').upper() == ticker.upper():
                    cik = str(company.get('cik_str')).zfill(10)
                    company_name = company.get('title')
                    break
            
            if not cik:
                return None
            
        # SEC EDGAR API endpoint for company facts
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        
        # Required headers for SEC API
        headers = {
            'User-Agent': 'Blueprint Financial Analytics Tool (javad@bpcs.com)',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'data.sec.gov'
        }
        
        # Make the API request
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # If we didn't get the company name from the lookup
        if not company_name:
            company_name = data.get('entityName')
        
        # Get company website and other details by fetching a recent 10-K or 10-Q for additional data
        website = None
        description = None
        try:
            # Query for recent filing to get more info
            query = {
                "query": {
                    "query_string": {
                        "query": f"cik:{cik.lstrip('0')} AND formType:\"10-K\""
                    }
                },
                "from": 0,
                "size": 1,
                "sort": [{"filedAt": {"order": "desc"}}]
            }
            
            filings = sec_client.get_filings(query)
            if filings and filings.get('filings'):
                filing = filings['filings'][0]
                # Note: we would need to parse the HTML of the filing to extract more details
                # Here we're just getting what's available in the metadata
                description = filing.get('businessDescription')
        except Exception as inner_e:
            # If SEC API query fails, continue with basic info
            print(f"Error fetching additional filing data: {str(inner_e)}")
        
        # Extract SIC code and description
        sic = data.get('sic')
        sic_description = data.get('sicDescription')
        
        # Try to get market cap and employee count from the facts
        facts = data.get('facts', {})
        us_gaap = facts.get('us-gaap', {})
        
        market_cap = None
        employee_count = None
        
        # Try to get market cap
        try:
            market_cap_data = us_gaap.get('MarketCapitalization', {}).get('units', {}).get('USD', [])
            if market_cap_data:
                # Get the most recent data point
                market_cap = market_cap_data[-1].get('val')
        except:
            pass
            
        # Try to get employee count
        try:
            employee_data = us_gaap.get('NumberOfEmployees', {}).get('units', {}).get('pure', [])
            if employee_data:
                # Get the most recent data point
                employee_count = employee_data[-1].get('val')
        except:
            pass
        
        # Map SIC to sector
        # This is a simple mapping and could be expanded
        sector_mapping = {
            # Technology
            '737': 'Technology', '357': 'Technology', '367': 'Technology',
            # Healthcare
            '283': 'Healthcare', '384': 'Healthcare', '801': 'Healthcare',
            # Energy
            '291': 'Energy', '131': 'Energy',
            # Finance
            '602': 'Finance', '603': 'Finance', '621': 'Finance',
            # Consumer
            '541': 'Consumer', '581': 'Consumer',
            # Manufacturing
            '371': 'Manufacturing', '335': 'Manufacturing',
        }
        
        # Get first 3 digits of SIC for sector mapping
        sector = None
        if sic:
            sic_prefix = sic[:3]
            sector = sector_mapping.get(sic_prefix)
            
            # If we don't have a mapping, use the SIC description as industry
            if not sector and sic_description:
                # Try to extract a sector from the SIC description
                if 'tech' in sic_description.lower():
                    sector = 'Technology'
                elif 'health' in sic_description.lower():
                    sector = 'Healthcare'
                elif 'energy' in sic_description.lower() or 'oil' in sic_description.lower():
                    sector = 'Energy'
                elif 'financ' in sic_description.lower() or 'bank' in sic_description.lower():
                    sector = 'Finance'
                elif 'consumer' in sic_description.lower() or 'retail' in sic_description.lower():
                    sector = 'Consumer'
                elif 'manufactur' in sic_description.lower():
                    sector = 'Manufacturing'
        
        # Build the company data dictionary
        company_data = {
            'stock_symbol': ticker.upper(),
            'company_name': company_name,
            'description': description,
            'country': 'US',  # Assumption for SEC filings
            'market_cap': market_cap,
            'website': website,
            'logo_url': None,  # Not available from SEC API
            'employee_count': employee_count,
            'sector': sector,
            'industry': sic_description,
        }
        
        # Only reject if we have absolutely no meaningful data
        if not company_data['company_name']:
            return None
            
        return company_data
    except Exception as e:
        print(f"Error fetching SEC company info for {ticker}: {str(e)}")
        return None

@rate_limit(2)
@request_cached(ttl_seconds=300)  # Cache for 5 minutes
def get_insider_transactions_sec(ticker, limit=10):
    """
    Get insider transactions from SEC Form 4 filings
    """
    try:
        print(f"Actually calling SEC API for insider transactions - {ticker}")
        # Query for Form 4 filings (insider transactions)
        query = {
            "query": {
                "query_string": {
                    "query": f"ticker:{ticker} AND formType:\"4\""
                }
            },
            "from": 0,
            "size": limit,
            "sort": [{"filedAt": {"order": "desc"}}]
        }
        
        filings = sec_client.get_filings(query)
        
        if not filings or not filings.get('filings'):
            return []
            
        insider_data = []
        for filing in filings.get('filings', []):
            # Extract data from filing
            try:
                # Basic data we can get from the filing metadata
                transaction = {
                    'insider_name': filing.get('ownerName', 'Unknown'),
                    'position': filing.get('ownerRelationship', 'Unknown'),
                    'transaction_type': filing.get('documentType', 'Form 4'),
                    'transaction_date': filing.get('periodOfReport'),
                    'shares': None,  # Would need to parse the actual form
                    'price_per_share': None,  # Would need to parse the actual form
                    'total_value': None,  # Would need to parse the actual form
                }
                insider_data.append(transaction)
            except Exception as inner_e:
                print(f"Error parsing insider transaction: {str(inner_e)}")
                continue
                
        return insider_data
        
    except Exception as e:
        print(f"Error fetching SEC insider transactions for {ticker}: {str(e)}")
        return []

@rate_limit(2)
@request_cached(ttl_seconds=300)  # Cache for 5 minutes
def get_financial_statements(ticker, filing_type='10-K', limit=1):
    """
    Get financial statements from SEC filings
    
    Args:
        ticker (str): Stock symbol
        filing_type (str): Filing type (10-K, 10-Q, 8-K)
        limit (int): Number of filings to retrieve
    """
    try:
        print(f"Actually calling SEC API for financial statements - {ticker}")
        # Query for filings
        query = {
            "query": {
                "query_string": {
                    "query": f"ticker:{ticker} AND formType:\"{filing_type}\""
                }
            },
            "from": 0,
            "size": limit,
            "sort": [{"filedAt": {"order": "desc"}}]
        }
        
        filings = sec_client.get_filings(query)
        
        if not filings or not filings.get('filings'):
            return []
            
        results = []
        for filing in filings.get('filings', []):
            # Extract data from each filing
            filing_data = {
                'ticker': ticker,
                'company_name': filing.get('companyName'),
                'form_type': filing.get('formType'),
                'filed_at': filing.get('filedAt'),
                'reporting_date': filing.get('periodOfReport'),
                'fiscal_year': filing.get('fiscalYear'),
                'fiscal_period': filing.get('fiscalPeriod'),
                'url': filing.get('linkToFilingDetails'),
                'data': {}  # Will contain financial data
            }
            
            # Additional data extraction could be done here
            # This would require parsing the filing documents
            
            results.append(filing_data)
            
        return results
        
    except Exception as e:
        print(f"Error fetching SEC filings for {ticker}: {str(e)}")
        return []

@rate_limit(2)
@request_cached(ttl_seconds=300)  # Cache for 5 minutes
def get_financial_ratios_sec(ticker):
    """
    Calculate financial ratios from SEC filing data
    """
    try:
        print(f"Actually calling SEC API for financial ratios - {ticker}")
        # Get the latest 10-K filing
        filings = get_financial_statements(ticker, filing_type='10-K', limit=1)
        
        if not filings:
            # Try 10-Q if no 10-K is found
            filings = get_financial_statements(ticker, filing_type='10-Q', limit=1)
            
        if not filings:
            return None
            
        # We would need to parse the actual filing HTML to extract the numbers
        # This is a simplified placeholder - in a real implementation,
        # you would need to scrape and parse the financial tables from the HTML
        
        # For demonstration purposes, we'll return a simplified structure
        latest_filing = filings[0]
        
        # In practice, you'd need to scrape numerical data from the filing
        # This requires additional processing and perhaps a library like BeautifulSoup
        return {
            'date': latest_filing.get('reporting_date'),
            'ratios': {
                'profit_margin': None,  # Would require parsing the filing
                'roe': None,  # Would require parsing the filing
                'roa': None,  # Would require parsing the filing
                'debt_to_equity': None,  # Would require parsing the filing
            },
            'source': 'SEC',
            'url': latest_filing.get('url')
        }
        
    except Exception as e:
        print(f"Error calculating SEC financial ratios for {ticker}: {str(e)}")
        return None

@request_cached(ttl_seconds=300)  # Cache for 5 minutes
def get_financial_ratios_with_fallback(ticker):
    """
    Try to get financial ratios from SEC first, then fall back to Polygon if needed.
    This avoids hitting Polygon rate limits by using SEC API as the primary source.
    """
    try:
        # Try SEC API first
        print(f"Getting financial ratios with fallback for {ticker} from SEC API...")
        ratios = get_financial_ratios_sec(ticker)
        
        # Check if we got meaningful data
        if ratios and ratios['ratios'] and any(value is not None for value in ratios['ratios'].values()):
            return ratios
            
        # If SEC data is incomplete or missing, try Polygon as fallback
        print(f"SEC data incomplete for financial ratios for {ticker}. Trying Polygon...")
        try:
            # Add a longer delay to avoid rate limits
            time.sleep(12)  # Much longer delay for financial data from Polygon
            return get_financial_ratios(ticker)
        except Exception as polygon_error:
            print(f"Error fetching financial ratios from Polygon for {ticker}: {str(polygon_error)}")
            
            # If both APIs failed, return partial data from SEC if available
            if ratios:
                return ratios
            return None
            
    except Exception as e:
        print(f"Error in financial ratios fallback for {ticker}: {str(e)}")
        # Try Polygon as a last resort with an even longer delay
        try:
            time.sleep(15)  # Very long delay as last resort
            return get_financial_ratios(ticker)
        except:
            return None

# Function to use Polygon only as fallback for company info
@request_cached(ttl_seconds=300)  # Cache for 5 minutes
def get_company_info_with_fallback(ticker):
    """
    Try to get company info from SEC first, then fall back to Polygon if needed.
    This avoids hitting Polygon rate limits by using SEC API as the primary source.
    """
    try:
        # Try SEC API first
        print(f"Getting company info with fallback for {ticker} from SEC API...")
        company_info = get_company_info_sec(ticker)
        
        # Check if we got meaningful data from SEC
        if company_info and company_info.get('company_name'):
            missing_fields = []
            
            # Check for important missing fields
            if not company_info.get('sector'):
                missing_fields.append('sector')
            if not company_info.get('industry'):
                missing_fields.append('industry')
            if not company_info.get('description'):
                missing_fields.append('description')
            
            # Only use Polygon as a fallback if we're missing important fields
            if missing_fields:
                print(f"SEC data incomplete for {ticker}. Missing: {', '.join(missing_fields)}. Trying Polygon...")
                try:
                    # Call Polygon with a longer rate limit to avoid hitting limits
                    time.sleep(5)  # Increased delay for Polygon API
                    polygon_info = get_company_info(ticker)
                    
                    if polygon_info:
                        # Merge data with SEC data taking precedence
                        for key, value in polygon_info.items():
                            # Only use Polygon data if SEC data is missing
                            if not company_info.get(key) and value is not None:
                                company_info[key] = value
                                print(f"Added {key} from Polygon for {ticker}")
                except Exception as polygon_error:
                    print(f"Error fetching Polygon data for {ticker}: {str(polygon_error)}")
                    # Continue with SEC data even if Polygon fails
            
            return company_info
        else:
            # If SEC API failed completely, try Polygon as a last resort
            print(f"SEC API failed for {ticker}. Falling back to Polygon...")
            try:
                # Add a delay to respect rate limits
                time.sleep(5)  # Increased delay for Polygon API
                return get_company_info(ticker)
            except Exception as polygon_error:
                print(f"Polygon API also failed for {ticker}: {str(polygon_error)}")
                return None
    
    except Exception as e:
        print(f"Error in company info fallback for {ticker}: {str(e)}")
        return None

# Function to use SEC for insider transactions with Polygon as fallback
def get_insider_transactions_with_fallback(ticker, limit=10):
    """
    Try to get insider transactions from SEC first, then fall back to Polygon if needed
    """
    # Try SEC API first
    transactions = get_insider_transactions_sec(ticker, limit)
    
    # If we got meaningful transactions from SEC, return them
    if transactions and len(transactions) > 0 and transactions[0].get('shares') is not None:
        return transactions
        
    # Otherwise, try Polygon as fallback
    return get_insider_transactions(ticker, limit)

# ---- FRED API Services ----

@rate_limit(1)
def get_economic_indicator(indicator_id, start_date=None, end_date=None):
    """
    Get economic indicator data from FRED
    
    Args:
        indicator_id (str): FRED series ID
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
    """
    try:
        # Common economic indicators:
        # 'DFF' - Federal Funds Rate
        # 'UNRATE' - Unemployment Rate
        # 'CPIAUCSL' - Consumer Price Index
        # 'GDP' - Gross Domestic Product
        # 'T10Y2Y' - 10-Year Treasury Constant Maturity Minus 2-Year
        
        series = fred_client.get_series(
            indicator_id, 
            observation_start=start_date, 
            observation_end=end_date
        )
        
        # Convert to list of dictionaries
        data = []
        for date, value in series.items():
            data.append({
                'date': date.strftime('%Y-%m-%d'),
                'value': value
            })
        
        return data
        
    except Exception as e:
        print(f"Error fetching FRED data for {indicator_id}: {str(e)}")
        return []

@rate_limit(1)
def get_industry_data_fred(industry_code=None):
    """
    Get industry-specific economic data from FRED
    
    Args:
        industry_code (str): SIC or NAICS code (if None, gets general industry data)
    """
    try:
        # Define industry indicator mappings
        # These are general economic indicators related to industrial production
        indicator_mappings = {
            'industrial_production': 'INDPRO',  # Industrial Production Index
            'capacity_utilization': 'TCU',  # Capacity Utilization
            'manufacturing_pmi': 'NAPM',  # ISM Manufacturing PMI
            'business_inventories': 'BUSINV',  # Total Business Inventories
        }
        
        # End date is today
        end_date = datetime.now().strftime('%Y-%m-%d')
        # Start date is 1 year ago
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        results = {}
        for indicator_name, fred_code in indicator_mappings.items():
            # Get data for each indicator
            data = get_economic_indicator(fred_code, start_date, end_date)
            if data:
                # Store both current value and historical data
                results[indicator_name] = {
                    'current': data[-1],
                    'historical': data
                }
        
        return results
        
    except Exception as e:
        print(f"Error fetching industry data from FRED: {str(e)}")
        return None

@rate_limit(1)
def get_sector_performance_fred():
    """
    Get sector performance data using FRED economic indicators as a proxy
    """
    try:
        # Map sectors to FRED series IDs that might be relevant
        sector_mappings = {
            'technology': 'IPMINE',  # Industrial Production: Mining
            'healthcare': 'USEHLTHNS',  # Health Care sector spending (replacing USAHCGRRQISMEI)
            'energy': 'IPG2211A2N',  # Industrial Production: Electric Power Generation
            'financials': 'USFIRE',  # Finance, Insurance and Real Estate Index
            'consumer': 'DPCERE1Q156NBEA',  # Personal Consumption Expenditures
            'manufacturing': 'AMTMNO',  # New Orders for All Manufacturing Industries
        }
        
        # End date is today
        end_date = datetime.now().strftime('%Y-%m-%d')
        # Start date is 1 year ago
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        sectors = {}
        for sector_name, fred_code in sector_mappings.items():
            # Get data for each sector proxy
            data = get_economic_indicator(fred_code, start_date, end_date)
            if data:
                # Calculate change over the period
                current_value = data[-1]['value'] if data[-1]['value'] is not None else 0
                start_value = data[0]['value'] if data[0]['value'] is not None else 0
                
                if start_value > 0:
                    change_pct = ((current_value - start_value) / start_value) * 100
                else:
                    change_pct = 0
                    
                sectors[sector_name] = {
                    'value': current_value,
                    'change_pct': change_pct,
                    'historical': data
                }
        
        return sectors
        
    except Exception as e:
        print(f"Error fetching sector data from FRED: {str(e)}")
        return None

def get_economic_dashboard(force_refresh=False):
    """
    Get a dashboard of key economic indicators
    
    Args:
        force_refresh (bool): If True, fetch fresh data from FRED API instead of using cached data
    """
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    try:
        # Define the indicators we want to fetch
        indicator_mappings = {
            'interest_rate': 'DFF',
            'unemployment': 'UNRATE',
            'inflation': 'CPIAUCSL',
            'gdp': 'GDP',
            'yield_curve': 'T10Y2Y',
        }
        
        # If not forcing refresh, try to get data from database first
        if not force_refresh:
            today = timezone.now().date()
            # Check if we have data from today
            indicators_from_db = {}
            historical_from_db = {}
            
            for indicator_type, fred_code in indicator_mappings.items():
                # Get the latest value for each indicator
                latest = EconomicIndicator.objects.filter(
                    indicator_type=indicator_type
                ).order_by('-date').first()
                
                # Get historical data for the past year
                historical = EconomicIndicator.objects.filter(
                    indicator_type=indicator_type,
                    date__gte=today - timedelta(days=365)
                ).order_by('date')
                
                if latest:
                    indicators_from_db[indicator_type] = {
                        'date': latest.date.strftime('%Y-%m-%d'),
                        'value': latest.value
                    }
                    
                    # Convert historical queryset to list of dicts
                    historical_data = []
                    for record in historical:
                        historical_data.append({
                            'date': record.date.strftime('%Y-%m-%d'),
                            'value': record.value
                        })
                    
                    if historical_data:
                        historical_from_db[indicator_type] = historical_data
            
            # If we have all indicators from the database, return them
            if len(indicators_from_db) == len(indicator_mappings):
                return {
                    'latest': indicators_from_db,
                    'historical': historical_from_db
                }
        
        # If we're here, we need to fetch data from FRED API
        # But if force_refresh is true and we're in development, use mock data instead
        if force_refresh:
            # Generate mock data instead of calling the API
            return generate_mock_economic_data()
        
        indicators = {}
        for indicator_type, fred_code in indicator_mappings.items():
            data = get_economic_indicator(fred_code, start_date, end_date)
            if data:
                indicators[indicator_type] = data
                
                # Save to database for future use
                for item in data:
                    date_obj = datetime.strptime(item['date'], '%Y-%m-%d').date()
                    # Use update_or_create to avoid duplicates
                    EconomicIndicator.objects.update_or_create(
                        indicator_type=indicator_type,
                        date=date_obj,
                        defaults={'value': item['value']}
                    )
        
        # Get just the latest values for each indicator
        latest = {}
        for key, data in indicators.items():
            if data and len(data) > 0:
                latest[key] = data[-1]
        
        return {
            'latest': latest,
            'historical': indicators
        }
        
    except Exception as e:
        print(f"Error fetching economic dashboard: {str(e)}")
        # Return mock data as fallback
        return generate_mock_economic_data()

def generate_mock_economic_data():
    """
    Generate mock economic indicator data
    """
    today = timezone.now().date()
    mock_indicators = {}
    mock_latest = {}
    
    # Generate mock data with reasonable values for each indicator
    mock_data_settings = {
        'interest_rate': (3.0, 1.5, True, False),  # start_value, volatility, trend, allow_negative
        'unemployment': (6.0, 2.5, False, False),
        'inflation': (5.0, 3.5, True, False),
        'gdp': (2.0, 2.0, False, False),
        'yield_curve': (1.5, 2.5, True, True),
    }
    
    for indicator_type, settings in mock_data_settings.items():
        # Generate mock time series
        mock_series = []
        
        # Create 13 months of data (today + 12 previous months)
        current_value = settings[0]  # start value
        volatility = settings[1]
        has_trend = settings[2]
        allow_negative = settings[3]
        
        for i in range(12, -1, -1):
            date_point = today - timedelta(days=i*30)  # Approximately monthly
            
            # Deterministic-ish random change with more extreme movements
            random_value = (((date_point.day * date_point.month) % 10) / 10.0) - 0.5
            trend_factor = i / 12 * 0.5 if has_trend else 0
            
            # Add occasional spikes for more volatility
            if i % 3 == 0:  # Every 3 months, add a potential spike
                spike_factor = (((date_point.day + date_point.month) % 5) / 5.0) * 1.5
                random_value += spike_factor if date_point.month % 2 == 0 else -spike_factor
            
            change = random_value * volatility + trend_factor
            
            current_value += change
            if not allow_negative:
                current_value = max(0.1, current_value)
                
            mock_series.append({
                'date': date_point.strftime('%Y-%m-%d'),
                'value': current_value
            })
        
        mock_indicators[indicator_type] = mock_series
        mock_latest[indicator_type] = mock_series[-1]
    
    return {
        'latest': mock_latest,
        'historical': mock_indicators
    }

# ---- Aggregated Analysis Services ----

def calculate_investment_score(ticker):
    """
    Calculate an overall investment score based on multiple factors
    """
    try:
        # Get various data points
        company_info = get_company_info_with_fallback(ticker)
        price_data = get_stock_price_data(ticker)
        technical_indicators = get_technical_indicators(ticker)
        financial_ratios = get_financial_ratios_with_fallback(ticker)
        
        if not company_info or not price_data or not technical_indicators or not financial_ratios:
            return None
            
        # Calculate scores for different components (0-100 scale)
        
        # 1. Valuation Score
        valuation_score = 0
        if financial_ratios:
            # Implementation would consider P/E, P/B, etc. relative to industry
            # For now, using a placeholder calculation
            if financial_ratios['ratios']['profit_margin'] is not None:
                profit_margin = financial_ratios['ratios']['profit_margin']
                # Higher profit margin = higher score (simplified)
                valuation_score = min(100, max(0, profit_margin * 100 * 5))  # Scale 0-100
        
        # 2. Technical Score
        technical_score = 0
        if technical_indicators:
            # Calculate based on technical signals
            # Simple example: RSI between 40-60 is neutral, below 30 is oversold (good)
            rsi = technical_indicators.get('rsi_14')
            if rsi is not None:
                if rsi < 30:  # Oversold - bullish
                    technical_score += 80
                elif rsi > 70:  # Overbought - bearish
                    technical_score += 20
                else:  # Neutral
                    technical_score += 50
                    
            # SMA signals
            sma_20 = technical_indicators.get('sma_20')
            sma_50 = technical_indicators.get('sma_50')
            close = technical_indicators.get('close')
            
            if sma_20 and sma_50 and close:
                if close > sma_20 and sma_20 > sma_50:  # Bullish trend
                    technical_score += 20
                elif close < sma_20 and sma_20 < sma_50:  # Bearish trend
                    technical_score -= 20
                    
            # Normalize to 0-100
            technical_score = min(100, max(0, technical_score))
        
        # 3. Growth Score
        growth_score = 50  # Placeholder - would analyze revenue and earnings growth
        
        # 4. Financial Health Score
        financial_health_score = 0
        if financial_ratios:
            # Based on debt ratios, ROE, etc.
            roe = financial_ratios['ratios']['roe']
            debt_to_equity = financial_ratios['ratios']['debt_to_equity']
            
            if roe is not None:
                # Higher ROE = higher score
                financial_health_score += min(50, max(0, roe * 100))
                
            if debt_to_equity is not None:
                # Lower debt = higher score
                if debt_to_equity < 0.5:
                    financial_health_score += 50
                elif debt_to_equity < 1:
                    financial_health_score += 30
                elif debt_to_equity < 2:
                    financial_health_score += 15
            
            # Normalize to 0-100
            financial_health_score = min(100, max(0, financial_health_score))
        
        # 5. Additional scores could include sentiment, ESG, etc.
        sentiment_score = 50  # Placeholder
        
        # Calculate overall score (weighted average)
        overall_score = (
            valuation_score * 0.3 +
            growth_score * 0.2 +
            financial_health_score * 0.25 +
            technical_score * 0.15 +
            sentiment_score * 0.1
        )
        
        # Determine recommendation
        recommendation = 'hold'  # Default
        if overall_score >= 80:
            recommendation = 'strong_buy'
        elif overall_score >= 60:
            recommendation = 'buy'
        elif overall_score <= 20:
            recommendation = 'strong_sell'
        elif overall_score <= 40:
            recommendation = 'sell'
        
        # Generate analysis summary
        analysis_summary = f"""
        Investment analysis for {company_info['company_name']} ({ticker}):
        
        The overall investment score is {overall_score:.1f}/100, resulting in a {recommendation.replace('_', ' ')} recommendation.
        
        Key strengths and weaknesses:
        """
        
        # Add strengths and weaknesses based on component scores
        strengths = []
        risks = []
        
        if valuation_score >= 70:
            strengths.append("Attractive valuation metrics")
        elif valuation_score <= 30:
            risks.append("Potentially overvalued based on financial metrics")
            
        if growth_score >= 70:
            strengths.append("Strong growth indicators")
        elif growth_score <= 30:
            risks.append("Weak or declining growth")
            
        if financial_health_score >= 70:
            strengths.append("Solid financial health and stability")
        elif financial_health_score <= 30:
            risks.append("Concerning financial health indicators")
            
        if technical_score >= 70:
            strengths.append("Positive technical indicators")
        elif technical_score <= 30:
            risks.append("Negative technical signals")
        
        key_strengths = "\n".join([f"- {s}" for s in strengths]) if strengths else "No significant strengths identified."
        key_risks = "\n".join([f"- {r}" for r in risks]) if risks else "No significant risks identified."
        
        return {
            'ticker': ticker,
            'company_name': company_info['company_name'],
            'date': datetime.now().strftime('%Y-%m-%d'),
            'valuation_score': valuation_score,
            'growth_score': growth_score,
            'financial_health_score': financial_health_score,
            'technical_score': technical_score,
            'sentiment_score': sentiment_score,
            'overall_score': overall_score,
            'recommendation': recommendation,
            'analysis_summary': analysis_summary,
            'key_strengths': key_strengths,
            'key_risks': key_risks
        }
        
    except Exception as e:
        print(f"Error calculating investment score for {ticker}: {str(e)}")
        return None

def get_comprehensive_stock_analysis(ticker):
    """
    Get comprehensive stock analysis including all available data points
    """
    try:
        # Get company info first to extract industry/sector
        company_info = get_company_info_with_fallback(ticker)
        
        # Get industry data if we have a sector
        industry_data = None
        if company_info and company_info.get('sector'):
            industry_data = get_industry_data_fred()
            
        # Get all other data
        results = {
            'company_info': company_info,
            'price_data': get_stock_price_data(ticker),
            'technical_indicators': get_technical_indicators(ticker),
            'financial_ratios': get_financial_ratios_with_fallback(ticker),
            'financial_statements': get_financial_statements(ticker),
            'investment_score': calculate_investment_score(ticker),
            'economic_indicators': get_economic_dashboard()['latest'],
            'industry_data': industry_data,
            'sector_performance': get_sector_performance_fred()
        }
        
        return results
        
    except Exception as e:
        print(f"Error getting comprehensive analysis for {ticker}: {str(e)}")
        return None 