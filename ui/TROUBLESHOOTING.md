# Troubleshooting Guide

## Common Issues and Solutions

### 1. Mixed Content Error (HTTPS/HTTP Mismatch)

**Problem:** UI is on HTTPS but API is on HTTP, causing browser to block requests.

**Solutions:**
- **Option A:** Use HTTP for both UI and API
  - Change API URL to: `http://13.60.80.172`
  - Host UI on HTTP instead of HTTPS

- **Option B:** Use HTTPS for both UI and API
  - Configure your API server to use HTTPS
  - Update API URL to: `https://13.60.80.172`

- **Option C:** Use the built-in fallback
  - The UI now automatically tries HTTP if HTTPS fails
  - Just use the default HTTPS URL

### 2. CORS Error

**Problem:** API server doesn't allow cross-origin requests.

**Solution:** Add CORS headers to your API server:
```python
# In your FastAPI app
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. Network Connection Error

**Problem:** Cannot connect to API server.

**Solutions:**
- Check if API server is running
- Verify the API URL is correct
- Check firewall settings
- Ensure the server is accessible from your network

### 4. API Server Not Responding

**Problem:** API server is down or not responding.

**Solutions:**
- Restart the API server
- Check server logs for errors
- Verify all required environment variables are set
- Check if the server is listening on the correct port

### 5. TypeError: Cannot read properties of undefined

**Problem:** JavaScript trying to access properties of undefined object.

**Solution:** This is usually caused by network errors. The UI now handles this better with:
- Better error handling
- Null checks
- Fallback mechanisms

## Quick Fixes

### For HTTPS/HTTP Issues:
1. Open the UI
2. Go to Configuration section
3. Change API URL to: `http://13.60.80.172`
4. Click "Update URL"
5. Test with "Health Check"

### For CORS Issues:
1. Add CORS middleware to your API server
2. Restart the API server
3. Test again

### For Network Issues:
1. Check if API server is running: `curl http://13.60.80.172/health`
2. Verify network connectivity
3. Check firewall settings

## Testing Your API

### Manual Testing:
```bash
# Health check
curl http://13.60.80.172/health

# Network test
curl http://13.60.80.172/network/test

# Coin search
curl -X POST http://13.60.80.172/coin/search \
  -H "Content-Type: application/json" \
  -d '{"query": "bitcoin"}'
```

### Using the UI:
1. Start with "Health Check"
2. Try "Network Test"
3. Test "Search Bitcoin"
4. Use "Chat with Naomi"

## Debug Information

### Browser Console:
- Open Developer Tools (F12)
- Check Console tab for errors
- Check Network tab for failed requests

### API Server Logs:
- Check your API server console/logs
- Look for error messages
- Verify all endpoints are working

### Common Error Messages:
- `Failed to fetch`: Network connectivity issue
- `Mixed Content`: HTTPS/HTTP mismatch
- `CORS`: Cross-origin request blocked
- `404`: Endpoint not found
- `500`: Server error

## Getting Help

If you're still having issues:
1. Check the browser console for specific error messages
2. Test the API manually with curl
3. Verify your API server configuration
4. Check network connectivity
5. Review the API documentation 