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

# Send message function
def send_message(chat_id, text, parse_mode='HTML'):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        }
        response = requests.post(url, json=payload)
        logger.info(f"Message sent to {chat_id}: {response.status_code}")
        return response.json()
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return None

# Home route
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': 'marketplace bot is running',
        'message': 'eFootball Marketplace Bot',
        'endpoints': ['/webhook', '/set_webhook', '/get_webhook']
    })

# Webhook endpoint with LAUNCH BUTTON
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        logger.info(f"📩 Received: {data}")
        
        if data and 'message' in data:
            chat_id = data['message']['chat']['id']
            text = data['message'].get('text', '')
            first_name = data['message']['from'].get('first_name', '')
            username = data['message']['from'].get('username', '')
            
            if text == '/start':
                # Create inline keyboard with LAUNCH BUTTON
                keyboard = {
                    'inline_keyboard': [[
                        {
                            'text': '🛒 Open Marketplace',  # LAUNCH BUTTON
                            'web_app': {'url': APP_URL}      # Opens the app
                        }
                    ]]
                }
                
                welcome = f"""
👋 Welcome {first_name} to eFootball Marketplace!

Buy and sell eFootball accounts securely.

• Browse accounts for sale
• Post your own account
• Contact trusted admins
• Secure transactions

👇 Click the button below to open the marketplace:
                """
                
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                payload = {
                    'chat_id': chat_id,
                    'text': welcome,
                    'parse_mode': 'HTML',
                    'reply_markup': keyboard  # This adds the button
                }
                requests.post(url, json=payload)
                logger.info(f"✅ Welcome sent to {chat_id}")
            
            elif text == '/help':
                help_text = """
<b>📚 Available Commands:</b>

/start - Open marketplace with launch button
/help - Show this message
/status - Check bot status
                """
                send_message(chat_id, help_text)
            
            elif text == '/status':
                send_message(chat_id, "✅ Bot is running normally")
            
            else:
                send_message(chat_id, "Use /start to open the marketplace")
        
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

@app.route('/delete_webhook', methods=['GET'])
def delete_webhook():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
    response = requests.get(url)
    return jsonify(response.json())

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    logger.info(f"🤖 Marketplace Bot starting on port {port}")
    logger.info(f"🚀 Launch button URL: {APP_URL}")
    app.run(host='0.0.0.0', port=port)
