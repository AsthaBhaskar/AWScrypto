# Naomi Crypto Assistant - Web UI

A modern, responsive web interface for testing the Naomi Crypto Assistant API.

## 🚀 Features

- **Real-time API Testing**: Test all 12 API endpoints directly from the browser
- **Quick Actions**: One-click access to common operations
- **Live Status Monitoring**: Real-time API health checks
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Interactive Tabs**: Organized interface for different API categories
- **JSON Response Viewer**: Formatted display of API responses
- **Performance Metrics**: Response time tracking

## 📁 Files

- `index.html` - Main UI interface
- `styles.css` - Additional styling and animations
- `README.md` - This documentation

## 🛠️ Setup

1. **Download the UI files** to your local machine
2. **Open `index.html`** in any modern web browser
3. **Configure the API URL** (default: http://13.60.80.172)
4. **Start testing!**

## 🎯 Quick Start

1. **Health Check**: Click "Health Check" to verify API status
2. **Test Bitcoin**: Click "Search Bitcoin" for a quick coin analysis
3. **Chat with Naomi**: Click "Chat with Naomi" to test conversational AI
4. **Network Test**: Click "Network Test" to check external API connectivity

## 📊 Available Endpoints

### Health & Diagnostics
- `GET /health` - API health check
- `GET /network/test` - Network connectivity test

### Coin Data
- `POST /coin/search` - Search for coins
- `GET /coin/{coin_id}/details` - Get coin details
- `GET /coin/{coin_id}/performance` - Historical performance

### Smart Money Analytics
- `POST /smart-money/flow` - Smart money flow data

### Social Sentiment
- `POST /social/sentiment` - Social sentiment analysis
- `GET /social/trending` - Trending hashtags
- `GET /social/influencers` - Influencer mentions

### AI & Analysis
- `POST /conversation` - Chat with Naomi
- `POST /analysis` - Comprehensive crypto analysis

## 🎨 UI Sections

### Quick Actions
- **Health Check**: Verify API is running
- **Network Test**: Check external API connectivity
- **Search Bitcoin**: Quick Bitcoin analysis
- **Chat with Naomi**: Test conversational AI

### Coin Analysis
- **Coin Symbol**: Enter any cryptocurrency symbol
- **Analysis Type**: Choose analysis focus (Price, Performance, Smart Money, Social)
- **Timeframe**: Select time period for analysis

### API Endpoints (Tabbed Interface)
- **Coin Data Tab**: Search, details, and performance
- **Smart Money Tab**: On-chain analytics
- **Social Tab**: Sentiment and trending data

### System Info
- **API Status**: Real-time health indicator
- **Last Request**: Track recent API calls
- **Response Time**: Performance monitoring

## 🔧 Customization

### Change API URL
Edit the `API_BASE` constant in the JavaScript section:

```javascript
const API_BASE = 'http://your-api-url.com';
```

### Add New Endpoints
1. Add new tab content in the HTML
2. Create corresponding JavaScript function
3. Use the `makeRequest()` helper function

### Styling
- Modify `styles.css` for custom styling
- Update color scheme in CSS variables
- Add new animations and effects

## 📱 Mobile Support

The UI is fully responsive and works on:
- Desktop browsers (Chrome, Firefox, Safari, Edge)
- Tablets (iPad, Android tablets)
- Mobile phones (iPhone, Android)

## 🎯 Usage Tips

1. **Start with Health Check**: Always verify API is running first
2. **Use Quick Actions**: For common operations, use the quick action buttons
3. **Check Response Times**: Monitor performance in the System Info section
4. **Read Error Messages**: Detailed error information is displayed in the response area
5. **Try Different Analysis Types**: Test various analysis intents for comprehensive testing

## 🔍 Troubleshooting

### API Not Responding
- Check if the API server is running
- Verify the API URL is correct
- Check network connectivity

### CORS Issues
- Ensure the API server allows CORS requests
- Check browser console for error messages

### Response Errors
- Review the error message in the response area
- Check API documentation for correct request format
- Verify required parameters are provided

## 🚀 Deployment

### Local Testing
Simply open `index.html` in a web browser.

### Web Server Deployment
Upload the UI files to any web server:
- Apache
- Nginx
- GitHub Pages
- Netlify
- Vercel

### Docker Deployment
```dockerfile
FROM nginx:alpine
COPY . /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## 📞 Support

For issues with the UI:
1. Check browser console for JavaScript errors
2. Verify API endpoint responses
3. Test with different browsers
4. Check network connectivity

For API-related issues, refer to the main API documentation.

---

**Happy testing! 🚀💰** 