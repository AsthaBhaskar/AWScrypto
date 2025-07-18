#!/usr/bin/env python3
"""
Test script for enhanced crypto assistant functionality
"""

import os
from dotenv import load_dotenv
from coingecko_tool import search_coin_id, get_coin_details
from nansen_tool import get_comprehensive_smart_money_flow, get_token_address_from_coingecko
from twitter_tool import get_social_sentiment

# Load environment variables
load_dotenv()

def test_enhanced_workflow():
    """Test the enhanced workflow with a sample coin"""
    
    print("🧪 Testing Enhanced Crypto Assistant Workflow")
    print("=" * 50)
    
    # Test coin
    symbol = "sol"
    
    print(f"🔍 Testing with {symbol.upper()}")
    
    # Step 1: Get coin details from CoinGecko
    print("\n1. Getting coin details from CoinGecko...")
    coin_id = search_coin_id(symbol)
    if coin_id:
        print(f"   ✅ Found coin ID: {coin_id}")
        
        coin_details = get_coin_details(coin_id)
        if coin_details.get("status") == "success":
            print(f"   ✅ Coin details retrieved")
            print(f"   📊 Price: ${coin_details.get('current_price', 'N/A')}")
            print(f"   📈 24h: {coin_details.get('price_change_24h', 'N/A')}%")
            print(f"   📈 7d: {coin_details.get('price_change_7d', 'N/A')}%")
            print(f"   🏗️ Chain: {coin_details.get('chain', 'N/A')}")
            print(f"   🔗 Contract: {coin_details.get('contract_address', 'N/A')}")
            
            # Step 2: Get smart money flow data
            print("\n2. Getting smart money flow data...")
            chain = coin_details.get("chain")
            contract_address = coin_details.get("contract_address")
            
            if chain and contract_address:
                smart_money_data = get_comprehensive_smart_money_flow(chain, contract_address)
                if smart_money_data.get("status") == "success":
                    print("   ✅ Smart money data retrieved")
                    print(f"   📊 Summary: {smart_money_data.get('summary', 'N/A')}")
                    if "analysis" in smart_money_data:
                        analysis = smart_money_data["analysis"]
                        print(f"   🎯 Recommendation: {analysis.get('recommendation', 'N/A')}")
                        print(f"   📈 Sentiment: {analysis.get('overall_sentiment', 'N/A')}")
                else:
                    print(f"   ❌ Smart money data error: {smart_money_data.get('result', 'Unknown error')}")
            else:
                print("   ⚠️ No chain or contract address available for smart money analysis")
            
            # Step 3: Get social sentiment
            print("\n3. Getting social sentiment...")
            social_data = get_social_sentiment(symbol)
            if social_data:
                print(f"   ✅ Social sentiment: {social_data}")
            else:
                print("   ⚠️ Social sentiment data unavailable")
            
            print("\n✅ Enhanced workflow test completed!")
            
        else:
            print(f"   ❌ Failed to get coin details: {coin_details.get('result', 'Unknown error')}")
    else:
        print(f"   ❌ Could not find coin ID for {symbol}")

if __name__ == "__main__":
    test_enhanced_workflow() 