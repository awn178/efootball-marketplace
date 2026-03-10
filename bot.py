import os
import requests
import logging
from flask import Flask, request, jsonify

# NEW BOT TOKEN for marketplace
BOT_TOKEN = "8581114593:AAFlLTXXaMChMohb_co9G6oGo-EQ3GYF4ak"
APP_URL = "https://efootball-marketplace.onrender.com"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({'status': 'marketplace bot running', 'bot': '@ElBICHO_MARKETBOT'})

@app.route('/test', methods=['GET'])
def test():
    return "✅ Bot test endpoint working!"

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return jsonify({'message': 'Webhook active', 'bot': '@ElBICHO_MARKETBOT'})
    
    try:
        data = request.json
        logger.info(f"📩 Received: {data}")
        
        if data and 'message' in data:
            chat_id = data['message']['chat']['id']
            text = data['message'].get('text', '')
            first_name = data['message']['from'].get('first_name', '')
            
            if text == '/start':
                # Create launch button
                keyboard = {
                    'inline_keyboard': [[
                        {
                            'text': '🛒 Open Marketplace',
                            'web_app': {'url': APP_URL}
                        }
                    ]]
                }
                
                welcome = f"👋 Welcome {first_name} to eFootball Marketplace!\n\nClick below to open:"
                
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                payload = {
                    'chat_id': chat_id,
                    'text': welcome,
                    'reply_markup': keyboard
                }
                requests.post(url, json=payload)
                logger.info(f"✅ Welcome sent to {chat_id}")
        
        return {'ok': True}
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return {'ok': False}, 500

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
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🤖 Marketplace Bot starting on port {port}")
    app.run(host='0.0.0.0', port=port)
