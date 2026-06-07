# Stock Research MCP
# This gives Claude the ability to look up stock prices and info

import httpx
import json

API_KEY = "YOUR_API_KEY_HERE"

def get_stock_price(ticker: str) -> dict:
    """Look up the current price of a stock by ticker symbol."""
    
    url = f"https://www.alphavantage.co/query"
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": ticker,
        "apikey": API_KEY
    }
    
    response = httpx.get(url, params=params)
    data = response.json()
    
    quote = data.get("Global Quote", {})
    
    return {
        "ticker": ticker.upper(),
        "price": quote.get("05. price", "N/A"),
        "change": quote.get("09. change", "N/A"),
        "change_percent": quote.get("10. change percent", "N/A"),
        "volume": quote.get("06. volume", "N/A")
    }


# Test it
if __name__ == "__main__":
    result = get_stock_price("AAPL")
    print(json.dumps(result, indent=2))
