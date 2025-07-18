# Naomi AI Agent 🤖💜

A sophisticated AI-powered crypto market analyst built with advanced language models and real-time data integration. Naomi combines the power of Grok-4, CoinGecko, Nansen, and Twitter APIs to provide comprehensive cryptocurrency analysis with a unique personality.

## 🌟 Features

### 🤖 **Advanced AI Integration**
- **Grok-4 Powered**: Leverages xAI's latest language model for intelligent responses
- **Context-Aware**: Understands crypto terminology and market dynamics
- **Personality-Driven**: Naomi's confident, witty Gen Z style makes crypto analysis engaging

### 📊 **Real-Time Market Data**
- **Live Price Data**: Current prices, market cap, volume from CoinGecko
- **Performance Tracking**: 1h, 24h, 7d, 30d price changes and trends
- **Smart Money Flow**: Nansen integration for whale movements and institutional flows
- **Social Sentiment**: Twitter sentiment analysis for community mood

### 🔒 **Content Safety**
- **Prohibited Content Filtering**: Blocks inappropriate, illegal, or harmful content
- **Crypto Context Awareness**: Distinguishes legitimate crypto terms from prohibited content
- **Ambiguous Query Handling**: Requests clarification for unclear requests
- **False-Negative Rate**: <0.1% for robust safety measures

### 💬 **Conversational Intelligence**
- **Intent Classification**: Automatically detects price queries, performance analysis, on-chain data requests
- **Multi-Coin Analysis**: Handles queries about multiple cryptocurrencies simultaneously
- **Fallback Responses**: Graceful handling of API timeouts and errors
- **Conversation Memory**: Maintains context across interactions

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- API keys for:
  - Grok-4 (xAI)
  - CoinGecko (free tier available)
  - Nansen (optional, for smart money data)
  - Twitter API (optional, for sentiment analysis)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/insightlabs-ai/NaomiAIAgent.git
   cd NaomiAIAgent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   # Create .env file
   echo "GROK_API_KEY=your_grok_api_key_here" > .env
   echo "NANSEN_API_KEY=your_nansen_api_key_here" >> .env
   echo "TWITTER_API_KEY=your_twitter_api_key_here" >> .env
   ```

4. **Run the assistant**
   ```bash
   python crypto_assistant.py
   ```

## 💻 Usage Examples

### Basic Price Queries
```
> price of bitcoin
Naomi: Bitcoin's absolutely crushing it at $67,420! 🚀

> tell me about ethereum
Naomi: ETH is sitting pretty at $3,469 with a solid 9.99% gain in 24h. 
Market cap: $418B, Volume: $63.8B. Pretty wild times in crypto, right? 💜
```

### Performance Analysis
```
> what is the performance of chainlink
Naomi: LINK is showing some serious moves! 
24h: +3.05%, 7d: +17.61%, 30d: +25.47%
Market cap: $11.5B, Volume: $908M
The smart money is definitely paying attention! 🔗
```

### Smart Money & Social Sentiment
```
> smart money flow for solana
Naomi: SOL's got the whales moving! 
Smart money flow: +$2.1M in 24h
Social sentiment: Bullish (78% positive mentions)
Price: $177.50 (+5.2% 24h)
The institutional flow is looking spicy! 🌟
```

## 🛠️ Technical Architecture

### Core Components

- **`crypto_assistant.py`**: Main application with conversation handling and intent classification
- **`grok_model.py`**: Grok-4 API integration and response generation
- **`coingecko_tool.py`**: CoinGecko API wrapper for market data
- **`nansen_tool.py`**: Nansen API integration for smart money analytics
- **`twitter_tool.py`**: Twitter sentiment analysis
- **`conversation_tool.py`**: Casual conversation handling

### Data Flow
1. **User Input** → Content safety filtering
2. **Intent Classification** → Route to appropriate tools
3. **Data Collection** → Fetch from multiple APIs
4. **Analysis Synthesis** → Combine data with Grok-4
5. **Response Generation** → Naomi's personality-driven output

### API Integrations

| Service | Purpose | Rate Limits |
|---------|---------|-------------|
| **CoinGecko** | Market data, prices, performance | 50 calls/min (free) |
| **Nansen** | Smart money flow, whale tracking | Varies by plan |
| **Twitter** | Social sentiment analysis | 300 requests/15min |
| **Grok-4** | AI response generation | Varies by plan |

## 🔧 Configuration

### Environment Variables
```bash
GROK_API_KEY=your_grok_api_key
NANSEN_API_KEY=your_nansen_api_key
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_secret
TWITTER_BEARER_TOKEN=your_bearer_token
```

### Content Safety Settings
- **Prohibited Keywords**: Configurable list of blocked terms
- **Fuzzy Matching**: 85% threshold for misspelling detection
- **Crypto Context**: Whitelist of legitimate crypto terminology
- **Escalation**: Repeated violation handling

## 📈 Performance & Reliability

### Error Handling
- **API Timeouts**: Automatic fallback to basic data
- **Rate Limiting**: Intelligent request throttling
- **Network Issues**: Graceful degradation
- **Invalid Data**: Validation and error reporting

### Response Quality
- **Completeness**: Always provides price and basic metrics
- **Accuracy**: Real-time data from trusted sources
- **Personality**: Consistent Naomi voice across all responses
- **Context**: Relevant analysis based on query intent

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Code formatting
black .
flake8 .
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **xAI** for Grok-4 API access
- **CoinGecko** for comprehensive market data
- **Nansen** for smart money analytics
- **Twitter** for social sentiment data
- **Insight Labs AI** for project development

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/insightlabs-ai/NaomiAIAgent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/insightlabs-ai/NaomiAIAgent/discussions)
- **Documentation**: [Wiki](https://github.com/insightlabs-ai/NaomiAIAgent/wiki)

---

**Built with 💜 by Insight Labs AI**

*Naomi: Ready to dive into the wild world of crypto? Let's make some moves! 🚀* 