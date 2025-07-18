# 🟣 Naomi Crypto Assistant

A sophisticated crypto assistant powered by xAI Grok and AWS Strands, designed with Naomi's unique Gen Z personality to provide real-time crypto insights, market data, and educational content.

## 🎯 Features

- **Real-time Price Data**: Fetch current prices from CoinGecko API
- **Advanced Intent Classification**: Smart detection of user queries using regex patterns
- **Naomi's Personality**: AI-powered responses with Gen Z energy and crypto expertise
- **Multi-tool Integration**: CoinGecko, Nansen (placeholder), Twitter (placeholder)
- **Conversation Memory**: Maintains context across interactions
- **Error Handling**: Graceful fallbacks and user-friendly error messages

## 🏗️ Architecture

### Complete Flow Diagram
```
User Input → Intent Classification → Tool Selection → API Calls → Response Generation → User Output
     ↓              ↓                    ↓              ↓              ↓              ↓
"price of SOL" → PRICE_QUERY → get_price() → CoinGecko → Naomi's Voice → "SOL is $176.62!"
```

### Components

1. **Intent Classification Engine**
   - Regex-based pattern matching
   - Supports: PRICE_QUERY, ONCHAIN_ANALYSIS, SOCIAL_SENTIMENT, GENERAL_CRYPTO, GENERAL_CHAT

2. **Tool Orchestration**
   - `coingecko_tool.py`: Real-time price data
   - `nansen_tool.py`: On-chain analytics (placeholder)
   - `twitter_tool.py`: Social sentiment (placeholder)

3. **Response Generation**
   - xAI Grok integration for personality-driven responses
   - Fallback responses for error handling
   - Context-aware conversation management

## 🚀 Setup

### 1. Environment Configuration
Create a `.env` file with your API keys:
```env
GROK_API_KEY=your_grok_api_key_here
NANSEN_API_KEY=your_nansen_api_key_here  # Optional
TWITTER_BEARER_TOKEN=your_twitter_token_here  # Optional
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Assistant
```bash
python crypto_assistant.py
```

## 💬 Usage Examples

### Price Queries
```
> what's the price of bitcoin
> how much is $ETH
> tell me the price of solana
> cost of BTC
```

### General Crypto Questions
```
> tell me about ethereum
> what is cardano
> explain defi
> how does blockchain work
```

### On-chain Analysis (Coming Soon)
```
> whale movements for SOL
> smart money flow BTC
> on-chain analysis ETH
```

### Social Sentiment (Coming Soon)
```
> twitter sentiment for DOGE
> social media hype around PEPE
> community reaction to BTC
```

## 🔧 Technical Details

### Intent Classification Patterns

**Price Queries:**
- `r"price.*\b(?:of|for)\b"`
- `r"how.*\b(?:much|price)\b"`
- `r"\$\w+"`
- `r"cost.*\b(?:of|for)\b"`

**On-chain Analysis:**
- `r"whale.*\b(?:movement|transfer)\b"`
- `r"smart.*\b(?:money|flow)\b"`
- `r"on.*chain"`

**Social Sentiment:**
- `r"sentiment"`
- `r"twitter"`
- `r"social.*\b(?:media|hype)\b"`

### Symbol Extraction Strategies

1. **$SYMBOL Pattern**: Extracts ticker after $ symbol
2. **Crypto Keywords**: Matches against 100+ known crypto names/symbols
3. **Last Word Fallback**: Uses the last word in the query

### API Integration

**CoinGecko:**
- Endpoint: `https://api.coingecko.com/api/v3/simple/price`
- Dynamic ID mapping for all listed cryptocurrencies
- Real-time USD price data

**xAI Grok:**
- Model: grok-4
- Temperature: 0.8 (for creative responses)
- Max tokens: 1000
- Personality-driven response generation

## 🎭 Naomi's Personality

Naomi is designed as a confident, playful, and sassy Gen Z crypto influencer who:
- Speaks with bold, chatty energy
- Uses sarcastic quips and "degen" terminology
- Advocates for crypto adoption
- Simplifies blockchain concepts
- Loves rare NFTs and horror movie memorabilia
- Never gives financial advice
- Stays within crypto/blockchain domain

## 🔮 Future Enhancements

### Phase 2: Nansen Integration
- Smart money flow tracking
- Whale wallet monitoring
- Token flow analysis
- DeFi protocol analytics

### Phase 3: Twitter Integration
- Real-time sentiment analysis
- Trending hashtag tracking
- Influencer mention monitoring
- Community reaction analysis

### Phase 4: Advanced Features
- Portfolio tracking
- Price alerts
- News aggregation
- Technical analysis
- Cross-chain analytics

## 🛠️ Development

### Adding New Tools
1. Create tool function with `@tool` decorator
2. Add to imports in `crypto_assistant.py`
3. Update intent classification patterns
4. Add routing logic in main loop

### Extending Intent Classification
1. Add new regex patterns to `classify_intent_and_extract_symbol()`
2. Create corresponding tool functions
3. Update routing logic

### Customizing Naomi's Personality
Modify the `NAOMI_SYSTEM_PROMPT` in `crypto_assistant.py` to adjust:
- Tone and style
- Knowledge areas
- Response patterns
- Limitations and boundaries

## 🐛 Troubleshooting

### Common Issues

**"GROK_API_KEY not found"**
- Ensure your `.env` file contains the correct API key
- Check that `python-dotenv` is installed

**"No CoinGecko id found"**
- The symbol might not be listed on CoinGecko
- Try using the full name instead of ticker (e.g., "bitcoin" instead of "btc")

**"Error fetching price"**
- Check your internet connection
- CoinGecko API might be temporarily unavailable
- Rate limiting might be in effect

### Debug Mode
Add debug prints to see the flow:
```python
print(f"Intent: {intent}, Symbol: {symbol}")
print(f"Tool Result: {tool_result}")
```

## 📝 License

This project is part of the AWS Strands educational assistant system.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Test thoroughly
5. Submit a pull request

---

**Built with ❤️ using AWS Strands, xAI Grok, and CoinGecko APIs** 