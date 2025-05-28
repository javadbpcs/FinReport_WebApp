import requests
import json
from typing import Dict, Optional

def get_company_metadata(ticker: str) -> Optional[Dict]:
    """
    Fetch company metadata from SEC EDGAR database.
    
    Args:
        ticker (str): Company stock ticker symbol
        
    Returns:
        Optional[Dict]: Company metadata if found, None otherwise
    """
    # SEC EDGAR API endpoint for company facts
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{ticker}.json"
    
    # Required headers for SEC API
    headers = {
        'User-Agent': 'Blueprint javad@bpcs.com',
        'Accept-Encoding': 'gzip, deflate',
        'Host': 'data.sec.gov'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Extract relevant metadata
        company_info = {
            'name': data.get('entityName'),
            'cik': data.get('cik'),
            'sic': data.get('sic'),
            'sic_description': data.get('sicDescription'),
            'industry': data.get('industry'),
            'sector': data.get('sector'),
            'employees': data.get('facts', {}).get('us-gaap', {}).get('NumberOfEmployees', {}).get('units', {}).get('USD', [{}])[-1].get('val'),
            'market_cap': data.get('facts', {}).get('us-gaap', {}).get('MarketCapitalization', {}).get('units', {}).get('USD', [{}])[-1].get('val')
        }
        
        return company_info
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

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