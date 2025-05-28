import os
import json
import requests
from typing import Dict, Optional, List
from datetime import datetime
from dotenv import load_dotenv
from agents import Agent, Runner, function_tool
from sec_api import QueryApi
import time

# Load environment variables
load_dotenv(override=True)

def fetch_sec_filings(ticker: str) -> Dict[str, str]:
    """
    Fetches both 10-K and 10-Q filings for the given ticker from SEC-API.
    Returns a dictionary with formatted excerpts of the filings.
    """
    api_key = os.getenv("SEC_API")
    if not api_key:
        raise ValueError("SEC_API environment variable is not set")

    # Initialize the SEC API client
    client = QueryApi(api_key=api_key)

    # Define headers required by SEC.gov
    sec_headers = {
        "User-Agent": "Blueprint Financial Analytics Tool (javad@bpcs.com)",
        "Accept-Encoding": "gzip, deflate"
    }

    def fetch_latest_filing(filing_type: str) -> str:
        try:
            query = {
                "query": {
                    "query_string": {
                        "query": f"ticker:{ticker} AND formType:\"{filing_type}\""
                    }
                },
                "from": 0,
                "size": 1,
                "sort": [{"filedAt": {"order": "desc"}}]
            }

            # Use the SEC API client to make the request
            filings = client.get_filings(query)
            
            if not filings or not filings.get("filings"):
                return f"No recent {filing_type} found for {ticker}."

            filing = filings["filings"][0]
            
            # Get both HTML and TXT URLs
            html_url = filing.get("linkToFilingDetails")
            txt_url = filing.get("linkToTxt")
            filed_at = filing.get("filedAt")
            
            # Try HTML URL first, then TXT if HTML fails
            doc_url = html_url if html_url else txt_url
            if not doc_url:
                return f"No document URL found for {filing_type}."

            print(f"\nFetching document from: {doc_url}")
            
            # Add a delay to respect SEC.gov rate limits
            time.sleep(0.1)  # 100ms delay between requests
            
            # Fetch the document content with proper SEC headers
            doc_response = requests.get(doc_url, headers=sec_headers)
            
            if doc_response.status_code != 200:
                print(f"Error response from SEC: {doc_response.status_code}")
                print(f"Response headers: {dict(doc_response.headers)}")
                print(f"Using URL: {doc_url}")
                return f"Failed to fetch document content: HTTP {doc_response.status_code}"

            doc_text = doc_response.text

            # Extract key sections
            sections = {
                "10-K": ["Item 7", "Item 8"],
                "10-Q": ["Item 2", "Item 1"]
            }
            
            relevant_sections = ""
            for section in sections.get(filing_type, []):
                start_idx = doc_text.find(section)
                if start_idx != -1:
                    next_item_idx = doc_text.find("Item", start_idx + len(section))
                    if next_item_idx != -1:
                        section_text = doc_text[start_idx:next_item_idx]
                        relevant_sections += f"\n\n{section}:\n{section_text[:2000]}..."

            # Print debug information if enabled
            print(f"\nExtracted Filing Information for {ticker} ({filing_type}):")
            print(f"Filing Date: {filed_at}")
            print(f"Source URL: {doc_url}")
            print(f"Number of sections found: {len(sections.get(filing_type, []))}")
            print(f"Total length of relevant sections: {len(relevant_sections)} characters")
            print("Sections included:", ", ".join(sections.get(filing_type, [])))
            print("-" * 80)

            return f"Filing Date: {filed_at}\nSource: {doc_url}\n{relevant_sections}"
            
        except Exception as e:
            print(f"Error fetching {filing_type} for {ticker}: {str(e)}")
            return f"Error: {str(e)}"

    return {
        "10-K": fetch_latest_filing("10-K"),
        "10-Q": fetch_latest_filing("10-Q")
    }

# if __name__ == "__main__":
    # Example usage
    # ticker_symbol = "AAPL"
    # analysis_report = fetch_sec_filings(ticker_symbol)
    # print(analysis_report["10-K"]) 
    # print(analysis_report["10-Q"]) 