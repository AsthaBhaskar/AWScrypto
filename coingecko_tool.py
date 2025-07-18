import os
import requests
from strands import tool
from dotenv import load_dotenv

load_dotenv()

@tool
def search_coin_id(query: str) -> str:
    """
    Searches CoinGecko for a coin ID, prioritizing Solana/Ethereum chain coins, then exact name, then symbol, then fallback.
    """
    api_key = os.getenv("COINGECKO_API_KEY")
    url = "https://pro-api.coingecko.com/api/v3/search" if api_key else "https://api.coingecko.com/api/v3/search"
    headers = {"x-cg-pro-api-key": api_key} if api_key else {}
    try:
        response = requests.get(url, params={"query": query}, headers=headers)
        response.raise_for_status()
        coins = response.json().get("coins", [])
        if not coins:
            return None
        query_lower = query.lower()
        # 1. Exact name match (prioritize solana/eth chains)
        sol_eth_coins = []
        for coin in coins:
            # Check for Solana/Ethereum in platforms or asset_platform_id
            platforms = coin.get("platforms", {})
            asset_platform_id = coin.get("asset_platform_id", "")
            if (
                ("solana" in platforms and platforms["solana"]) or
                ("ethereum" in platforms and platforms["ethereum"]) or
                asset_platform_id in ["solana", "ethereum"]
            ):
                sol_eth_coins.append(coin)
        # Try exact name match among sol/eth coins
        for coin in sol_eth_coins:
            if coin.get("name", "").lower() == query_lower:
                print(f"[DEBUG] CoinGecko ID for '{query}' (sol/eth name match): {coin.get('id')}")
                return coin.get("id")
        # Try exact symbol match among sol/eth coins
        for coin in sol_eth_coins:
            if coin.get("symbol", "").lower() == query_lower:
                print(f"[DEBUG] CoinGecko ID for '{query}' (sol/eth symbol match): {coin.get('id')}")
                return coin.get("id")
        # Fallback: first sol/eth coin
        if sol_eth_coins:
            print(f"[DEBUG] CoinGecko ID for '{query}' (sol/eth fallback): {sol_eth_coins[0].get('id')}")
            return sol_eth_coins[0].get("id")
        # 2. Exact name match (all coins)
        for coin in coins:
            if coin.get("name", "").lower() == query_lower:
                print(f"[DEBUG] CoinGecko ID for '{query}': {coin.get('id')}")
                return coin.get("id")
        # 3. Exact symbol match (all coins)
        for coin in coins:
            if coin.get("symbol", "").lower() == query_lower:
                print(f"[DEBUG] CoinGecko ID for '{query}': {coin.get('id')}")
                return coin.get("id")
        # 4. Fallback to first result
        print(f"[DEBUG] CoinGecko ID for '{query}': {coins[0].get('id')}")
        return coins[0].get("id")
    except Exception as e:
        print(f"[DEBUG] Error searching CoinGecko ID for '{query}': {e}")
        return None

@tool
def get_coin_details(coin_id: str) -> dict:
    """
    Fetches detailed cryptocurrency data from CoinGecko including historical performance data.
    """
    if not coin_id:
        return {"status": "error", "result": "Missing coin_id."}
    api_key = os.getenv("COINGECKO_API_KEY")
    headers = {"x-cg-pro-api-key": api_key} if api_key else {}
    base_url = "https://pro-api.coingecko.com/api/v3" if api_key else "https://api.coingecko.com/api/v3"
    url = f"{base_url}/coins/{coin_id}"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        print(f"[DEBUG] Raw CoinGecko data for '{coin_id}': {data}")
        market_data = data.get("market_data", {})
        current_price = market_data.get("current_price", {}).get("usd", None)
        if isinstance(current_price, (int, float)):
            current_price_fmt = f"{current_price:.2f}"
        else:
            current_price_fmt = "N/A"
        market_cap = market_data.get("market_cap", {}).get("usd", None)
        if isinstance(market_cap, (int, float)):
            market_cap_fmt = f"{market_cap:,.0f}"
        else:
            market_cap_fmt = "N/A"
        total_volume = market_data.get("total_volume", {}).get("usd", "N/A")
        high_24h = market_data.get("high_24h", {}).get("usd", "N/A")
        low_24h = market_data.get("low_24h", {}).get("usd", "N/A")
        price_change_1h = market_data.get("price_change_percentage_1h_in_currency", {}).get("usd", "N/A")
        price_change_24h = market_data.get("price_change_percentage_24h_in_currency", {}).get("usd", "N/A")
        price_change_7d = market_data.get("price_change_percentage_7d_in_currency", {}).get("usd", "N/A")
        price_change_30d = market_data.get("price_change_percentage_30d_in_currency", {}).get("usd", "N/A")
        asset_platform_id = data.get("asset_platform_id")
        is_native = not asset_platform_id and data.get("id") in ["solana", "ethereum", "binancecoin", "avalanche-2"]
        found_chain = data.get("id") if is_native else None
        contract_address = None
        if not is_native:
            supported_chains = ["solana", "ethereum", "arbitrum", "polygon", "avalanche", "base", "bnb"]
            platforms = data.get("platforms", {})
            for chain in supported_chains:
                if platforms.get(chain):
                    found_chain = chain
                    contract_address = platforms[chain]
                    break
        def format_percentage(value):
            if value == "N/A" or value is None:
                return "N/A"
            return f"{value:+.2f}%"
        performance_summary = []
        if price_change_1h != "N/A":
            performance_summary.append(f"1h: {format_percentage(price_change_1h)}")
        if price_change_24h != "N/A":
            performance_summary.append(f"24h: {format_percentage(price_change_24h)}")
        if price_change_7d != "N/A":
            performance_summary.append(f"7d: {format_percentage(price_change_7d)}")
        if price_change_30d != "N/A":
            performance_summary.append(f"30d: {format_percentage(price_change_30d)}")
        performance_text = " | ".join(performance_summary) if performance_summary else "No performance data available"
        result_summary = (
            f"Here's the tea on {data.get('name', 'this coin')}. "
            f"Current price: ${current_price_fmt}. "
            f"Market cap: ${market_cap_fmt}. "
            f"Performance: {performance_text}"
        )
        return {
            "status": "success",
            "coin_id": coin_id,
            "is_native_asset": is_native,
            "chain": found_chain,
            "contract_address": contract_address,
            "current_price": current_price_fmt,
            "market_cap": market_cap_fmt,
            "total_volume": total_volume,
            "high_24h": high_24h,
            "low_24h": low_24h,
            "price_change_1h": price_change_1h,
            "price_change_24h": price_change_24h,
            "price_change_7d": price_change_7d,
            "price_change_30d": price_change_30d,
            "result": result_summary,
        }
    except requests.exceptions.HTTPError as e:
        print(f"[DEBUG] CoinGecko API error: {e.response.status_code}")
        return {"status": "error", "result": f"CoinGecko API error: {e.response.status_code}"}
    except requests.exceptions.RequestException as e:
        print(f"[DEBUG] Network error: {e}")
        return {"status": "error", "result": f"Network error: {e}"}

@tool
def get_historical_performance(coin_id: str, timeframe: str = "all") -> dict:
    """
    Fetches historical performance data for a specific timeframe or all timeframes.
    """
    if not coin_id:
        return {"status": "error", "result": "Missing coin_id parameter."}
    coin_data = get_coin_details(coin_id)
    if coin_data["status"] != "success":
        return coin_data
    performance_data = {
        "1h": coin_data.get("price_change_1h", "N/A"),
        "24h": coin_data.get("price_change_24h", "N/A"),
        "7d": coin_data.get("price_change_7d", "N/A"),
        "30d": coin_data.get("price_change_30d", "N/A"),
    }
    def format_percentage(value):
        if value == "N/A" or value is None:
            return "N/A"
        return f"{value:+.2f}%"
    if timeframe == "all":
        summary = []
        for tf, value in performance_data.items():
            summary.append(f"{tf}: {format_percentage(value)}")
        result_summary = f"Performance breakdown for {coin_data.get('coin_id', 'this coin')}: {' | '.join(summary)}"
        return {
            "status": "success",
            "coin_id": coin_id,
            "performance_data": performance_data,
            "result": result_summary,
        }
    elif timeframe in performance_data:
        value = performance_data[timeframe]
        result_summary = f"Performance for {coin_data.get('coin_id', 'this coin')} over {timeframe}: {format_percentage(value)}"
        return {
            "status": "success",
            "coin_id": coin_id,
            "timeframe": timeframe,
            "performance": value,
            "result": result_summary,
        }
    else:
        return {
            "status": "error",
            "result": f"Invalid timeframe '{timeframe}'. Use '1h', '24h', '7d', '30d', or 'all'.",
        } 