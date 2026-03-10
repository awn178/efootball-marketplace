from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is working!"

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    return {"status": "ok", "message": "webhook ready"}

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)
