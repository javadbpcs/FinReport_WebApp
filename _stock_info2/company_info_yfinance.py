import yfinance as yf
from typing import Dict, Optional, List

def get_company_metadata(ticker: str) -> Optional[Dict]:
    """
    Fetch company metadata using yfinance.
    
    Args:
        ticker (str): Company stock ticker symbol
        
    Returns:
        Optional[Dict]: Company metadata if found, None otherwise
    """
    try:
        # Create a Ticker object
        company = yf.Ticker(ticker)
        
        # Get company info
        info = company.info
        
        # Extract relevant metadata
        company_info = {
            'name': info.get('longName'),
            'sector': info.get('sector'),
            'industry': info.get('industry'),
            'employees': info.get('fullTimeEmployees'),
            'market_cap': info.get('marketCap'),
            'description': info.get('longBusinessSummary'),
            'country': info.get('country'),
            'website': info.get('website'),
            'address': info.get('address1'),
            'city': info.get('city'),
            'state': info.get('state'),
            'zip': info.get('zip'),
            'phone': info.get('phone')
        }
        
        return company_info
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def search_companies(search_term: str, limit: int = 10) -> List[Dict]:
    """
    Search for companies by name using yfinance
    
    Args:
        search_term (str): Partial company name to search for
        limit (int): Maximum number of results to return
        
    Returns:
        List[Dict]: List of matching companies with their ticker symbols
    """
    try:
        # Use yfinance search functionality (which searches Yahoo Finance)
        tickers = yf.Tickers(search_term)
        
        # yfinance does not have a direct search method, so as a workaround,
        # we can try to get info for potential tickers based on the search term
        # This is not ideal but is the best we can do with yfinance
        
        results = []
        # This is a simplified approach and might not return ideal results
        # since yfinance doesn't have a proper company search function
        for ticker in tickers.tickers:
            try:
                info = tickers.tickers[ticker].info
                results.append({
                    'stock_symbol': ticker,
                    'company_name': info.get('longName', info.get('shortName', ticker)),
                    'sector': info.get('sector', None),
                    'industry': info.get('industry', None),
                    'country': info.get('country', None)
                })
                if len(results) >= limit:
                    break
            except:
                continue
                
        return results
        
    except Exception as e:
        print(f"Error searching companies with term '{search_term}': {str(e)}")
        return []

if __name__ == "__main__":
    # Example usage
    ticker = "AAPL"  # Apple Inc.
    company_data = get_company_metadata(ticker)
    
    if company_data:
        print("Company Information:")
        for key, value in company_data.items():
            print(f"{key}: {value}")
    else:
        print("Failed to fetch company data") 