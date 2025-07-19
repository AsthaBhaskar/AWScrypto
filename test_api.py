#!/usr/bin/env python3
"""
Test script for Naomi Crypto Assistant API
Demonstrates how to use all the API endpoints
"""

import requests
import json
import time
from typing import Dict, Any

# API base URL
BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_network_connectivity():
    """Test network connectivity"""
    print("🌐 Testing network connectivity...")
    response = requests.get(f"{BASE_URL}/network/test")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_coin_search():
    """Test coin search endpoint"""
    print("🔍 Testing coin search...")
    data = {"query": "bitcoin"}
    response = requests.post(f"{BASE_URL}/coin/search", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_coin_details():
    """Test coin details endpoint"""
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
    """Test historical performance endpoint"""
    print("📈 Testing historical performance...")
    response = requests.get(f"{BASE_URL}/coin/bitcoin/performance?timeframe=7d")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_smart_money_flow():
    """Test smart money flow endpoint"""
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
    """Test social sentiment endpoint"""
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
    """Test trending hashtags endpoint"""
    print("🔥 Testing trending hashtags...")
    response = requests.get(f"{BASE_URL}/social/trending")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_influencer_mentions():
    """Test influencer mentions endpoint"""
    print("👑 Testing influencer mentions...")
    response = requests.get(f"{BASE_URL}/social/influencers?symbol=bitcoin")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_conversation():
    """Test conversation endpoint"""
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
    """Test comprehensive analysis endpoint"""
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
    """Test root endpoint"""
    print("🏠 Testing root endpoint...")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def main():
    """Run all API tests"""
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