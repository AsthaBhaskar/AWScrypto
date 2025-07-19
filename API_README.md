# Naomi Crypto Assistant API

A comprehensive FastAPI-based REST API that exposes all crypto assistant functionalities programmatically. Powered by xAI Grok and multiple data sources including CoinGecko, Nansen, and Twitter.

## 🚀 Features

- **Coin Search & Details**: Find and get comprehensive information about any cryptocurrency
- **Smart Money Analytics**: On-chain flow analysis and trader behavior insights
- **Social Sentiment**: Twitter sentiment analysis and trending hashtags
- **Conversational AI**: Chat with Naomi using xAI Grok
- **Comprehensive Analysis**: Multi-source data synthesis with actionable insights
- **Network Diagnostics**: Test connectivity to external APIs
- **Content Safety**: Built-in content filtering and safety checks

## 📋 Prerequisites

- Python 3.8+
- Required API keys (see Environment Variables section)

## 🛠️ Installation

1. **Clone or download the project files**

2. **Install dependencies**:
   ```bash
   pip install -r api_requirements.txt
   ```

3. **Set up environment variables**:
   Create a `.env` file in the project root:
   ```env
   # Required
   GROK_API_KEY=your_grok_api_key_here
   
   # Optional (for enhanced features)
   COINGECKO_API_KEY=your_coingecko_pro_api_key_here
   NANSEN_API_KEY=your_nansen_api_key_here
   TWITTER_BEARER_TOKEN=your_twitter_bearer_token_here
   ```

4. **Run the API server**:
   ```bash
   python api_main.py
   ```

   Or using uvicorn directly:
   ```bash
   uvicorn api_main:app --host 0.0.0.0 --port 8000 --reload
   ```

## 🌐 API Endpoints

### Health & Diagnostics

- `GET /health` - Health check
- `GET /network/test` - Test network connectivity to external APIs

### Coin Data

- `POST /coin/search` - Search for a coin ID
- `GET /coin/{coin_id}/details` - Get detailed coin information
- `GET /coin/{coin_id}/performance` - Get historical performance data

### Smart Money Analytics

- `POST /smart-money/flow` - Get smart money flow data for tokens or native assets

### Social Sentiment

- `POST /social/sentiment` - Get social sentiment analysis
- `GET /social/trending` - Get trending crypto hashtags
- `GET /social/influencers` - Get influencer mentions for a coin

### AI & Analysis

- `POST /conversation` - Chat with Naomi (conversational AI)
- `POST /analysis` - Get comprehensive crypto analysis

## 📖 API Usage Examples

### 1. Search for a Coin

```bash
curl -X POST "http://localhost:8000/coin/search" \
     -H "Content-Type: application/json" \
     -d '{"query": "bitcoin"}'
```

**Response:**
```json
{
  "status": "success",
  "coin_id": "bitcoin"
}
```

### 2. Get Comprehensive Analysis

```bash
curl -X POST "http://localhost:8000/analysis" \
     -H "Content-Type: application/json" \
     -d '{
       "symbol": "bitcoin",
       "intent": "PRICE",
       "timeframe": "24h"
     }'
```

**Response:**
```json
{
  "status": "success",
  "analysis": "Naomi's AI-generated analysis here...",
  "data": {
    "coin_details": {...},
    "smart_money_data": {...},
    "social_data": {...},
    "analysis_intent": "PRICE",
    "timeframe": "24h"
  },
  "charts": "📈 Price Performance:\n24h: 🟢 +2.45%\n7d: 🔴 -1.23%\n\n💰 Smart Money Flow:\n..."
}
```

### 3. Chat with Naomi

```bash
curl -X POST "http://localhost:8000/conversation" \
     -H "Content-Type: application/json" \
     -d '{
       "message": "Hi Naomi!",
       "context": []
     }'
```

### 4. Get Smart Money Flow

```bash
curl -X POST "http://localhost:8000/smart-money/flow" \
     -H "Content-Type: application/json" \
     -d '{
       "chain": "ethereum",
       "token_address": "0xa0b86a33e6441b8c4c8c8c8c8c8c8c8c8c8c8c8c"
     }'
```

### 5. Get Social Sentiment

```bash
curl -X POST "http://localhost:8000/social/sentiment" \
     -H "Content-Type: application/json" \
     -d '{
       "symbol": "bitcoin",
       "coin_name": "Bitcoin"
     }'
```

## 🔧 Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROK_API_KEY` | ✅ | xAI Grok API key for AI responses |
| `COINGECKO_API_KEY` | ❌ | CoinGecko Pro API key (falls back to free tier) |
| `NANSEN_API_KEY` | ❌ | Nansen API key for smart money analytics |
| `TWITTER_BEARER_TOKEN` | ❌ | Twitter API v2 Bearer token for social sentiment |
| `PORT` | ❌ | Server port (default: 8000) |

### API Rate Limits

- **Free Tier**: Limited by external API rate limits
- **Pro Tier**: Enhanced rate limits with API keys
- **Smart Money**: Requires Nansen API key
- **Social Sentiment**: Requires Twitter Bearer token

## 📊 Response Formats

### Success Response
```json
{
  "status": "success",
  "data": {...},
  "message": "Optional message"
}
```

### Error Response
```json
{
  "status": "error",
  "message": "Error description"
}
```

## 🛡️ Content Safety

The API includes built-in content safety features:

- **Prohibited Content Detection**: Filters inappropriate requests
- **Crypto Context Awareness**: Distinguishes legitimate crypto terms from prohibited content
- **Fuzzy Matching**: Catches misspellings and variations
- **Ambiguous Content Handling**: Requests clarification for unclear queries

## 🔍 API Documentation

Once the server is running, you can access:

- **Interactive API Docs**: http://localhost:8000/docs (Swagger UI)
- **Alternative Docs**: http://localhost:8000/redoc (ReDoc)
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## 🚀 Deployment

### Local Development
```bash
python api_main.py
```

### Production Deployment
```bash
# Using uvicorn
uvicorn api_main:app --host 0.0.0.0 --port 8000 --workers 4

# Using gunicorn
gunicorn api_main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "api_main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🔧 Troubleshooting

### Common Issues

1. **GROK_API_KEY not found**
   - Ensure your `.env` file contains the GROK_API_KEY
   - Check that the key is valid and active

2. **Network connectivity issues**
   - Use `/network/test` endpoint to diagnose connection problems
   - Check firewall settings and internet connection

3. **Rate limiting**
   - Add API keys for enhanced rate limits
   - Implement exponential backoff in your client code

4. **Content safety violations**
   - Review your request content
   - Ensure requests are crypto-related

### Debug Mode

Enable debug logging by setting the log level:
```bash
uvicorn api_main:app --log-level debug
```

## 📈 Performance Tips

1. **Caching**: Implement client-side caching for frequently requested data
2. **Rate Limiting**: Respect API rate limits and implement backoff strategies
3. **Connection Pooling**: Use connection pooling for external API calls
4. **Async Operations**: The API is built with async support for better performance

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the API documentation at `/docs`
3. Test network connectivity with `/network/test`
4. Check your environment variables and API keys

---

**Happy crypto analyzing! 🚀💰** 