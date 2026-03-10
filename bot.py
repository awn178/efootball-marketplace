import os
import requests
import logging
from flask import Flask, request, jsonify

# Telegram Bot Token
BOT_TOKEN = "8406169991:AAHcP5z7eHiKiSFGlRH3fOSDQS5gkjK-0EM"
APP_URL = "https://efootball-marketplace.onrender.com"

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# TEST ENDPOINT - Add this first to verify the app is running
@app.route('/test', methods=['GET'])
def test():
    return "✅ Bot service is working!"

# Home route
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': 'marketplace bot is running',
        'message': 'eFootball Marketplace Bot',
        'endpoints': ['/test', '/webhook', '/set_webhook', '/get_webhook']
    })

# Webhook endpoint - handles both GET and POST
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    # Handle GET requests (for testing)
    if request.method == 'GET':
        return jsonify({
            'message': 'Webhook endpoint is active',
            'status': 'ready',
            'method': 'GET'
        })
    
    # Handle POST requests from Telegram
    try:
        data = request.json
        logger.info(f"📩 Received: {data}")
        
        if data and 'message' in data:
            chat_id = data['message']['chat']['id']
            text = data['message'].get('text', '')
            first_name = data['message']['from'].get('first_name', '')
            
            if text == '/start':
                # Create inline keyboard with launch button
                keyboard = {
                    'inline_keyboard': [[
                        {
                            'text': '🛒 Open Marketplace',
                            'web_app': {'url': APP_URL}
                        }
                    ]]
                }
                
                welcome = f"""
👋 Welcome {first_name} to eFootball Marketplace!

Buy and sell eFootball accounts securely.

👇 Click the button below to open the marketplace:
                """
                
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                payload = {
                    'chat_id': chat_id,
                    'text': welcome,
                    'parse_mode': 'HTML',
                    'reply_markup': keyboard
                }
                requests.post(url, json=payload)
                logger.info(f"✅ Welcome sent to {chat_id}")
            
            elif text == '/help':
                help_text = "Available commands: /start - Open marketplace"
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                            json={'chat_id': chat_id, 'text': help_text})
        
        return {'ok': True}
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return {'ok': False}, 500

# Webhook management
@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    webhook_url = f"{APP_URL}/webhook"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}"
    response = requests.get(url)
    return jsonify(response.json())

@app.route('/get_webhook', methods=['GET'])
def get_webhook():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
    response = requests.get(url)
    return jsonify(response.json())

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    logger.info(f"🤖 Marketplace Bot starting on port {port}")
    logger.info(f"📱 Test endpoint: https://efootball-marketplace-bot.onrender.com/test")
    app.run(host='0.0.0.0', port=port)
