#!/usr/bin/env python3
"""
Test script for Naomi Crypto Assistant API

Test Purpose:
    - Validate all major API endpoints for correct responses and error handling.
    - Ensure integration between FastAPI server and external data sources (CoinGecko, Nansen, Twitter, Grok).
    - Provide regression coverage for endpoint changes.

Setup:
    - Assumes API server is running at BASE_URL (default: http://localhost:8000)
    - Requires valid .env with necessary API keys loaded by the server
    - No explicit setup/teardown per test; each test is stateless and independent

Teardown:
    - No teardown required; tests do not modify server state or external data
"""

import requests
import json
import time
from typing import Dict, Any

# API base URL
BASE_URL = "http://localhost:8000"

def test_health():
    """
    Purpose:
        Test the /health endpoint of the Naomi Crypto Assistant API.
    Args:
        None
    Returns:
        None
    Exceptions:
        Prints error if request fails.
    """
    print("🔍 Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_network_connectivity():
    """
    Purpose:
        Test the /network/test endpoint for network connectivity.
    Args:
        None
    Returns:
        None
    Exceptions:
        Prints error if request fails.
    """
    print("🌐 Testing network connectivity...")
    response = requests.get(f"{BASE_URL}/network/test")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_coin_search():
    """
    Purpose:
        Test the /coin/search endpoint for coin ID search.
    Args:
        None
    Returns:
        None
    Exceptions:
        Prints error if request fails.
    """
    print("🔍 Testing coin search...")
    data = {"query": "bitcoin"}
    response = requests.post(f"{BASE_URL}/coin/search", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_coin_details():
    """
    Purpose:
        Test the /coin/{coin_id}/details endpoint for coin details.
    Args:
        None
    Returns:
        None
    Exceptions:
        Prints error if request fails.
    """
    print("📊 Testing coin details...")
    response = requests.get(f"{BASE_URL}/coin/bitcoin/details")
    print(f"Status: {response.status_code}")
    result = response.json()
    if result["status"] == "success":
        print(f"Coin: {result['data'].get('coin_id', 'N/A')}")
        print(f"Price: ${result['data'].get('current_price', 'N/A')}")
        print(f"24h Change: {result['data'].get('price_change_24h', 'N/A')}%")
    else:
        print(f"Error: {result['message']}")
    print()

def test_historical_performance():
    """
    Purpose:
        Test the /coin/{coin_id}/performance endpoint for historical performance.
    Args:
        None
    Returns:
        None
    Exceptions:
        Prints error if request fails.
    """
    print("📈 Testing historical performance...")
    response = requests.get(f"{BASE_URL}/coin/bitcoin/performance?timeframe=7d")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_smart_money_flow():
    """
    Purpose:
        Test the /smart-money/flow endpoint for smart money flow data.
    Args:
        None
    Returns:
        None
    Exceptions:
        Prints error if request fails.
    """
    print("💰 Testing smart money flow...")
    data = {
        "chain": "ethereum",
        "token_address": "0xa0b86a33e6441b8c4c8c8c8c8c8c8c8c8c8c8c8c"
    }
    response = requests.post(f"{BASE_URL}/smart-money/flow", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_social_sentiment():
    """
    Purpose:
        Test the /social/sentiment endpoint for social sentiment analysis.
    Args:
        None
    Returns:
        None
    Exceptions:
        Prints error if request fails.
    """
    print("📱 Testing social sentiment...")
    data = {
        "symbol": "bitcoin",
        "coin_name": "Bitcoin"
    }
    response = requests.post(f"{BASE_URL}/social/sentiment", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_trending_hashtags():
    """
    Purpose:
        Test the /social/trending endpoint for trending hashtags.
    Args:
        None
    Returns:
        None
    Exceptions:
        Prints error if request fails.
    """
    print("🔥 Testing trending hashtags...")
    response = requests.get(f"{BASE_URL}/social/trending")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_influencer_mentions():
    """
    Purpose:
        Test the /social/influencers endpoint for influencer mentions.
    Args:
        None
    Returns:
        None
    Exceptions:
        Prints error if request fails.
    """
    print("👑 Testing influencer mentions...")
    response = requests.get(f"{BASE_URL}/social/influencers?symbol=bitcoin")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_conversation():
    """
    Purpose:
        Test the /conversation endpoint for conversational AI.
    Args:
        None
    Returns:
        None
    Exceptions:
        Prints error if request fails.
    """
    print("💬 Testing conversation...")
    data = {
        "message": "Hi Naomi!",
        "context": []
    }
    response = requests.post(f"{BASE_URL}/conversation", json=data)
    print(f"Status: {response.status_code}")
    result = response.json()
    if result["status"] == "success":
        print(f"Naomi: {result['response']}")
    else:
        print(f"Error: {result['response']}")
    print()

def test_comprehensive_analysis():
    """
    Purpose:
        Test the /analysis endpoint for comprehensive crypto analysis.
    Args:
        None
    Returns:
        None
    Exceptions:
        Prints error if request fails.
    """
    print("🔬 Testing comprehensive analysis...")
    data = {
        "symbol": "bitcoin",
        "intent": "PRICE",
        "timeframe": "24h"
    }
    response = requests.post(f"{BASE_URL}/analysis", json=data)
    print(f"Status: {response.status_code}")
    result = response.json()
    if result["status"] == "success":
        print(f"Analysis: {result['analysis'][:200]}...")
        print(f"Charts: {result['charts'][:100]}...")
    else:
        print(f"Error: {result['message']}")
    print()

def test_root_endpoint():
    """
    Purpose:
        Test the root (/) endpoint for API metadata.
    Args:
        None
    Returns:
        None
    Exceptions:
        Prints error if request fails.
    """
    print("🏠 Testing root endpoint...")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def main():
    """
    Purpose:
        Run all API endpoint tests for the Naomi Crypto Assistant API.
    Args:
        None
    Returns:
        None
    Exceptions:
        Prints error if any test fails or if connection error occurs.
    """
    print("🚀 Starting Naomi Crypto Assistant API Tests")
    print("=" * 50)
    
    try:
        # Test basic endpoints
        test_health()
        test_root_endpoint()
        test_network_connectivity()
        
        # Test coin-related endpoints
        test_coin_search()
        test_coin_details()
        test_historical_performance()
        
        # Test smart money endpoints
        test_smart_money_flow()
        
        # Test social endpoints
        test_social_sentiment()
        test_trending_hashtags()
        test_influencer_mentions()
        
        # Test AI endpoints
        test_conversation()
        test_comprehensive_analysis()
        
        print("✅ All tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Make sure the API server is running on http://localhost:8000")
        print("   Run: python api_main.py")
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    main() 