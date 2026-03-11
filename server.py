import os
import json
import psycopg2
import psycopg2.extras
import uuid
import base64
import logging
import sys
import requests
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Setup logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
print("🛒 EFOOTBALL MARKETPLACE SERVER STARTING")

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Configuration
BOT_TOKEN = "8581114593:AAFlLTXXaMChMohb_co9G6oGo-EQ3GYF4ak"
OWNER_USERNAME = "awnowner"
ADMIN_USERNAME = "awnadmin"

# Database connection
def get_db():
    try:
        DATABASE_URL = os.environ.get('DATABASE_URL', '')
        if not DATABASE_URL:
            print("❌ DATABASE_URL is empty!")
            return None
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"❌ Database connection error: {str(e)}")
        raise e

# Send Telegram notification
def send_telegram(chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        requests.post(url, json=payload)
    except Exception as e:
        print(f"❌ Telegram error: {str(e)}")

# Initialize database tables
def init_db():
    try:
        conn = get_db()
        cur = conn.cursor()
        
        print("📦 Creating database tables...")
        
        # Users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_username VARCHAR(255) UNIQUE NOT NULL,
                pin VARCHAR(10) NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                admin_role VARCHAR(50),
                is_banned BOOLEAN DEFAULT FALSE,
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                chat_id BIGINT
            )
        """)
        
        # Listings table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id SERIAL PRIMARY KEY,
                seller_username VARCHAR(255) NOT NULL REFERENCES users(telegram_username),
                main_squad_screenshot TEXT NOT NULL,
                overbench_screenshot TEXT NOT NULL,
                price INTEGER NOT NULL,
                featured_players TEXT,
                special_skills TEXT,
                coin_amount INTEGER DEFAULT 0,
                trade_type VARCHAR(50) DEFAULT 'FOR SALE',
                link_type VARCHAR(50) DEFAULT 'KONAMI LINK',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                is_sold BOOLEAN DEFAULT FALSE
            )
        """)
        
        # Admins table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                telegram_username VARCHAR(255) UNIQUE NOT NULL,
                profile_photo TEXT,
                payment_method TEXT,
                is_super_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Skills table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id SERIAL PRIMARY KEY,
                skill_name VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert default skills
        default_skills = [
            'Low Screamer', 'Phenomenal Finishing', 'Blitz Curler', 'Edge Crossing',
            'Visionary Pass', 'Phenomenal Pass', 'Aerial Fort', 'Long Reach Tackle',
            'Fortress', 'Acceleration Burst', 'Momentum Dribbling', 'Magnetic Fit',
            'GK Directing Defense', 'GK Sprint Roar', 'Willpower', 'Bullet Header',
            'Game-Changing Pass', 'Attack Trigger'
        ]
        
        for skill in default_skills:
            cur.execute("INSERT INTO skills (skill_name) VALUES (%s) ON CONFLICT DO NOTHING", (skill,))
        
        # Insert owner admin
        cur.execute("""
            INSERT INTO users (telegram_username, pin, is_admin, admin_role) 
            VALUES (%s, %s, TRUE, 'owner') 
            ON CONFLICT (telegram_username) DO UPDATE SET is_admin = TRUE, admin_role = 'owner'
        """, (OWNER_USERNAME, '12604'))
        
        cur.execute("""
            INSERT INTO admins (name, telegram_username, is_super_admin) 
            VALUES (%s, %s, TRUE) 
            ON CONFLICT (telegram_username) DO NOTHING
        """, ('Owner', OWNER_USERNAME))
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ All database tables ready!")
        
    except Exception as e:
        print(f"❌ Database init error: {str(e)}")
        raise e

# Serve HTML files
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/detail/<int:listing_id>')
def detail(listing_id):
    return send_from_directory('.', 'detail.html')

@app.route('/post')
def post():
    return send_from_directory('.', 'post.html')

@app.route('/admin')
def admin():
    return send_from_directory('.', 'admin.html')

# THIS SERVES THE LOGIN HTML PAGE
@app.route('/login')
def login_page():
    return send_from_directory('.', 'login.html')

# ==================== TELEGRAM BOT ====================

@app.route('/bot', methods=['POST', 'GET'])
def bot_webhook():
    if request.method == 'GET':
        return jsonify({'status': 'bot active', 'bot': '@ElBICHO_MARKETBOT'})
    
    try:
        data = request.json
        print(f"🤖 Bot received: {data}")
        
        if data and 'message' in data:
            chat_id = data['message']['chat']['id']
            text = data['message'].get('text', '')
            first_name = data['message']['from'].get('first_name', '')
            username = data['message']['from'].get('username', '')
            
            # Save chat_id
            if username:
                conn = get_db()
                cur = conn.cursor()
                cur.execute("UPDATE users SET chat_id = %s WHERE telegram_username = %s", 
                           (chat_id, '@' + username))
                conn.commit()
                cur.close()
                conn.close()
            
            if text == '/start':
                keyboard = {
                    'inline_keyboard': [[
                        {'text': '🛒 Open Marketplace', 'web_app': {'url': 'https://efootball-marketplace.onrender.com'}}
                    ]]
                }
                welcome = f"👋 Welcome {first_name} to eFootball Marketplace!\n\nBuy and sell eFootball accounts securely."
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                payload = {'chat_id': chat_id, 'text': welcome, 'reply_markup': keyboard}
                requests.post(url, json=payload)
            
            elif text == '/listings':
                conn = get_db()
                cur = conn.cursor()
                cur.execute("SELECT price, trade_type FROM listings WHERE is_active = TRUE ORDER BY created_at DESC LIMIT 5")
                recent = cur.fetchall()
                cur.close()
                conn.close()
                
                if recent:
                    msg = "📋 Recent Listings:\n\n"
                    for r in recent:
                        msg += f"💰 {r[0]} ETB | {r[1]}\n"
                else:
                    msg = "No active listings."
                send_telegram(chat_id, msg)
            
            elif text == '/help':
                send_telegram(chat_id, "Commands: /start, /listings, /help")
            
            else:
                send_telegram(chat_id, "Use /start to open marketplace")
        
        return {'ok': True}
    except Exception as e:
        print(f"❌ Bot error: {e}")
        return {'ok': False}, 500

@app.route('/setbot', methods=['GET'])
def set_bot_webhook():
    webhook_url = "https://efootball-marketplace.onrender.com/bot"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}"
    response = requests.get(url)
    return jsonify(response.json())

# ==================== USER ENDPOINTS ====================

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.json
        username = data.get('telegram_username', '')
        pin = data.get('pin', '')
        chat_id = data.get('chat_id')
        
        if not username or not pin:
            return jsonify({'success': False, 'message': 'Username and PIN required'})
        
        if len(pin) < 4 or len(pin) > 6:
            return jsonify({'success': False, 'message': 'PIN must be 4-6 digits'})
        
        if not username.startswith('@'):
            username = '@' + username
        
        conn = get_db()
        cur = conn.cursor()
        
        # Check if user exists
        cur.execute("SELECT id FROM users WHERE telegram_username = %s", (username,))
        existing = cur.fetchone()
        
        if existing:
            cur.close()
            conn.close()
            return jsonify({'success': False, 'message': 'User already exists. Please login.'})
        
        # Create new user
        cur.execute("""
            INSERT INTO users (telegram_username, pin, chat_id) 
            VALUES (%s, %s, %s) RETURNING id
        """, (username, pin, chat_id))
        
        user_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'user_id': user_id, 'username': username})
        
    except Exception as e:
        print(f"❌ Register error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        username = data.get('telegram_username', '')
        pin = data.get('pin', '')
        chat_id = data.get('chat_id')
        
        if not username or not pin:
            return jsonify({'success': False, 'message': 'Username and PIN required'})
        
        if not username.startswith('@'):
            username = '@' + username
        
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("SELECT id, is_admin FROM users WHERE telegram_username = %s AND pin = %s", (username, pin))
        user = cur.fetchone()
        
        if not user:
            cur.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Invalid credentials or user not registered'})
        
        user_id = user[0]
        is_admin = user[1]
        
        if chat_id:
            cur.execute("UPDATE users SET chat_id = %s WHERE id = %s", (chat_id, user_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'user_id': user_id, 'is_admin': is_admin, 'username': username})
        
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== LISTINGS ====================

@app.route('/api/listings', methods=['GET'])
def get_listings():
    try:
        user = request.args.get('user')
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        if user:
            cur.execute("""
                SELECT * FROM listings 
                WHERE seller_username = %s 
                ORDER BY created_at DESC
            """, (user,))
        else:
            cur.execute("""
                SELECT * FROM listings 
                WHERE is_active = TRUE AND is_sold = FALSE 
                ORDER BY created_at DESC
            """)
        
        listings = cur.fetchall()
        result = []
        
        for l in listings:
            featured = l['featured_players'].split(',') if l['featured_players'] else []
            skills = l['special_skills'].split(',') if l['special_skills'] else []
            
            result.append({
                'id': l['id'],
                'seller': l['seller_username'],
                'main_screenshot': l['main_squad_screenshot'],
                'price': l['price'],
                'coin_amount': l['coin_amount'],
                'trade_type': l['trade_type'],
                'link_type': l['link_type'],
                'featured_players': featured[:4],
                'special_skills': skills,
                'created': l['created_at'].isoformat() if l['created_at'] else None
            })
        
        cur.close()
        conn.close()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/listing/<int:listing_id>', methods=['GET'])
def get_listing(listing_id):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cur.execute("SELECT * FROM listings WHERE id = %s", (listing_id,))
        listing = cur.fetchone()
        
        if not listing:
            return jsonify({'success': False, 'message': 'Not found'}), 404
        
        cur.execute("SELECT * FROM admins ORDER BY name")
        admins = cur.fetchall()
        
        admin_list = []
        for a in admins:
            admin_list.append({
                'id': a['id'],
                'name': a['name'],
                'telegram': a['telegram_username'],
                'profile_photo': a['profile_photo'],
                'payment': a['payment_method']
            })
        
        featured = listing['featured_players'].split(',') if listing['featured_players'] else []
        skills = listing['special_skills'].split(',') if listing['special_skills'] else []
        
        result = {
            'id': listing['id'],
            'seller': listing['seller_username'],
            'main_screenshot': listing['main_squad_screenshot'],
            'overbench_screenshot': listing['overbench_screenshot'],
            'price': listing['price'],
            'coin_amount': listing['coin_amount'],
            'trade_type': listing['trade_type'],
            'link_type': listing['link_type'],
            'featured_players': featured[:4],
            'special_skills': skills,
            'created': listing['created_at'].isoformat() if listing['created_at'] else None,
            'trusted_admins': admin_list
        }
        
        cur.close()
        conn.close()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/create_listing', methods=['POST'])
def create_listing():
    try:
        data = request.json
        seller = data.get('seller_username')
        main_screenshot = data.get('main_screenshot')
        overbench_screenshot = data.get('overbench_screenshot')
        price = data.get('price')
        featured = data.get('featured_players', [])
        skills = data.get('special_skills', [])
        coins = data.get('coin_amount', 0)
        trade_type = data.get('trade_type', 'FOR SALE')
        link_type = data.get('link_type', 'KONAMI LINK')
        
        if not all([seller, main_screenshot, overbench_screenshot, price]):
            return jsonify({'success': False, 'message': 'Missing fields'})
        
        conn = get_db()
        cur = conn.cursor()
        
        featured_str = ','.join(featured[:4])
        skills_str = ','.join(skills)
        
        cur.execute("""
            INSERT INTO listings 
            (seller_username, main_squad_screenshot, overbench_screenshot, price, 
             featured_players, special_skills, coin_amount, trade_type, link_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (seller, main_screenshot, overbench_screenshot, price, 
              featured_str, skills_str, coins, trade_type, link_type))
        
        listing_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'listing_id': listing_id})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/delete_listing/<int:listing_id>', methods=['DELETE'])
def delete_listing(listing_id):
    try:
        data = request.json
        username = data.get('username')
        
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("DELETE FROM listings WHERE id = %s AND seller_username = %s", (listing_id, username))
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== SKILLS ====================

@app.route('/api/skills', methods=['GET'])
def get_skills():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT skill_name FROM skills ORDER BY skill_name")
        skills = [s[0] for s in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(skills)
    except Exception as e:
        return jsonify([]), 500

# ==================== ADMIN ENDPOINTS ====================

# THIS IS THE FIXED ADMIN API LOGIN - renamed to admin_api_login
@app.route('/api/admin/login', methods=['POST'])
def admin_api_login():  # Renamed from admin_login to avoid conflict
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if username == 'awnowner' and password == '12604':
            return jsonify({'success': True, 'role': 'owner', 'username': username})
        elif username == 'awnadmin' and password == '11512':
            return jsonify({'success': True, 'role': 'admin', 'username': username})
        else:
            return jsonify({'success': False, 'message': 'Invalid credentials'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/listings', methods=['GET'])
def admin_listings():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM listings ORDER BY created_at DESC")
        listings = cur.fetchall()
        
        result = []
        for l in listings:
            result.append({
                'id': l['id'],
                'seller': l['seller_username'],
                'price': l['price'],
                'coin_amount': l['coin_amount'],
                'trade_type': l['trade_type'],
                'link_type': l['link_type'],
                'is_active': l['is_active'],
                'is_sold': l['is_sold'],
                'created': l['created_at'].isoformat() if l['created_at'] else None
            })
        
        cur.close()
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify([]), 500

@app.route('/api/admin/edit_listing', methods=['POST'])
def edit_listing():
    try:
        data = request.json
        listing_id = data.get('listing_id')
        price = data.get('price')
        coins = data.get('coin_amount')
        trade_type = data.get('trade_type')
        link_type = data.get('link_type')
        is_active = data.get('is_active')
        is_sold = data.get('is_sold')
        
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE listings SET 
                price = %s, coin_amount = %s, trade_type = %s, 
                link_type = %s, is_active = %s, is_sold = %s
            WHERE id = %s
        """, (price, coins, trade_type, link_type, is_active, is_sold, listing_id))
        
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/delete_listing', methods=['POST'])
def admin_delete_listing():
    try:
        data = request.json
        listing_id = data.get('listing_id')
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM listings WHERE id = %s", (listing_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/admins', methods=['GET'])
def get_admins():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM admins ORDER BY name")
        admins = cur.fetchall()
        
        result = []
        for a in admins:
            result.append({
                'id': a['id'],
                'name': a['name'],
                'telegram': a['telegram_username'],
                'profile_photo': a['profile_photo'],
                'payment': a['payment_method'],
                'is_super_admin': a['is_super_admin']
            })
        
        cur.close()
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify([]), 500

@app.route('/api/admin/admins', methods=['POST'])
def add_admin():
    try:
        data = request.json
        name = data.get('name')
        telegram = data.get('telegram')
        profile = data.get('profile_photo')
        payment = data.get('payment')
        
        if not telegram.startswith('@'):
            telegram = '@' + telegram
        
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO admins (name, telegram_username, profile_photo, payment_method)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (name, telegram, profile, payment))
        
        admin_id = cur.fetchone()[0]
        
        cur.execute("""
            INSERT INTO users (telegram_username, pin, is_admin, admin_role)
            VALUES (%s, 'admin123', TRUE, 'admin')
            ON CONFLICT (telegram_username) DO UPDATE SET is_admin = TRUE, admin_role = 'admin'
        """, (telegram,))
        
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True, 'admin_id': admin_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/admins/<int:admin_id>', methods=['PUT'])
def update_admin(admin_id):
    try:
        data = request.json
        name = data.get('name')
        telegram = data.get('telegram')
        profile = data.get('profile_photo')
        payment = data.get('payment')
        
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE admins SET 
                name = COALESCE(%s, name),
                telegram_username = COALESCE(%s, telegram_username),
                profile_photo = COALESCE(%s, profile_photo),
                payment_method = COALESCE(%s, payment_method)
            WHERE id = %s
        """, (name, telegram, profile, payment, admin_id))
        
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/admins/<int:admin_id>', methods=['DELETE'])
def delete_admin(admin_id):
    try:
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("SELECT telegram_username FROM admins WHERE id = %s", (admin_id,))
        admin = cur.fetchone()
        
        if admin:
            cur.execute("UPDATE users SET is_admin = FALSE, admin_role = NULL WHERE telegram_username = %s", (admin[0],))
        
        cur.execute("DELETE FROM admins WHERE id = %s", (admin_id,))
        
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/manual_post', methods=['POST'])
def manual_post():
    try:
        data = request.json
        seller = data.get('seller_username')
        main = data.get('main_screenshot')
        over = data.get('overbench_screenshot')
        price = data.get('price')
        coins = data.get('coin_amount', 0)
        trade_type = data.get('trade_type', 'FOR SALE')
        link_type = data.get('link_type', 'KONAMI LINK')
        
        if not all([seller, main, over, price]):
            return jsonify({'success': False, 'message': 'Missing fields'})
        
        conn = get_db()
        cur = conn.cursor()
        
        # Check if seller exists
        cur.execute("SELECT id FROM users WHERE telegram_username = %s", (seller,))
        user = cur.fetchone()
        
        if not user:
            import random
            default_pin = str(random.randint(1000, 9999))
            cur.execute("INSERT INTO users (telegram_username, pin) VALUES (%s, %s)", (seller, default_pin))
        
        cur.execute("""
            INSERT INTO listings 
            (seller_username, main_squad_screenshot, overbench_screenshot, price, 
             coin_amount, trade_type, link_type, featured_players, special_skills)
            VALUES (%s, %s, %s, %s, %s, %s, %s, '', '')
            RETURNING id
        """, (seller, main, over, price, coins, trade_type, link_type))
        
        listing_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'listing_id': listing_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/skills', methods=['POST', 'PUT', 'DELETE'])
def manage_skills():
    try:
        data = request.json
        action = data.get('action')
        skill = data.get('skill_name')
        new_name = data.get('new_name')
        
        conn = get_db()
        cur = conn.cursor()
        
        if action == 'add':
            cur.execute("INSERT INTO skills (skill_name) VALUES (%s)", (skill,))
        elif action == 'edit':
            cur.execute("UPDATE skills SET skill_name = %s WHERE skill_name = %s", (new_name, skill))
        elif action == 'delete':
            cur.execute("DELETE FROM skills WHERE skill_name = %s", (skill,))
        
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Initialize database
print("🚀 Initializing database...")
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Server starting on port {port}")
    print(f"🤖 Bot webhook: https://efootball-marketplace.onrender.com/bot")
    print(f"🔗 Set webhook: https://efootball-marketplace.onrender.com/setbot")
    app.run(host='0.0.0.0', port=port)
