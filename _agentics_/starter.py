from agents import Agent, Runner, function_tool
from dotenv import load_dotenv
import os
import requests
from typing import Dict


load_dotenv(override=True)

# @function_tool
# def fetch_sec_filings(ticker: str) -> dict:
    # """
    # Fetches the latest 10-K and 10-Q filings for the given ticker.
    # """
    # Placeholder implementation
    # In production, implement actual fetching logic using SEC's EDGAR API
    # filings = {
        # "10-K": "Content of the latest 10-K filing...",
        # "10-Q": "Content of the latest 10-Q filing..."
    # }
    # return filings

@function_tool
def fetch_sec_filings(ticker: str) -> Dict[str, str]:
    """
    Fetches the latest 10-K and 10-Q filings for the given ticker from SEC-API.
    Returns a dictionary with formatted excerpts of the filings.
    """
    api_key = os.getenv("SEC_API")
    headers = {"Authorization": api_key}
    base_url = "https://api.sec-api.io"

    def fetch_latest_filing(filing_type: str) -> str:
        query = {
            "query": {
                "query_string": {
                    "query": f"ticker:{ticker} AND formType:{filing_type}"
                }
            },
            "from": 0,
            "size": 1,
            "sort": [{"filedAt": {"order": "desc"}}]
        }
        search_url = f"{base_url}/filings/search"
        search_response = requests.post(search_url, json=query, headers=headers)
        search_data = search_response.json()

        if not search_data["filings"]:
            return f"No recent {filing_type} found for {ticker}."

        doc_url = search_data["filings"][0]["linkToTxt"]
        filed_at = search_data["filings"][0]["filedAt"]

        doc_text = requests.get(doc_url).text

        # Optionally limit length for model use
        max_length = 5000
        trimmed_text = doc_text[:max_length] + "\n...[truncated]" if len(doc_text) > max_length else doc_text

        return f"Filing Date: {filed_at}\nSource: {doc_url}\n\n{trimmed_text}"

    return {
        "10-K": fetch_latest_filing("10-K"),
        # "10-Q": fetch_latest_filing("10-Q")
    }



filing_analyzer_agent = Agent(
    name="FilingAnalyzer",
    instructions="""
    You are a financial analyst AI. Analyze the provided SEC filings (10-K and 10-Q) for the given company ticker.
    Extract key financial metrics such as revenue, net income, and earnings per share.
    Identify any significant changes or risks mentioned in the filings.
    Summarize your findings in a structured report.
    """,
    tools=[fetch_sec_filings]
)


def analyze_company_filings(ticker: str):
    prompt = f"Analyze the SEC filings for the company with ticker symbol {ticker}."
    result = Runner.run_sync(filing_analyzer_agent, prompt)
    return result.final_output

# Example usage
if __name__ == "__main__":
    ticker_symbol = "AAPL"
    analysis_report = analyze_company_filings(ticker_symbol)
    print(analysis_report)
