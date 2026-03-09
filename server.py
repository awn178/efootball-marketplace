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
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS

# Setup logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
print("🛒 EFOOTBALL MARKETPLACE SERVER STARTING")
print("✅ Debug mode ON")

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Configuration
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8406169991:AAHcP5z7eHiKiSFGlRH3fOSDQS5gkjK-0EM')
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

# Initialize database tables
def init_db():
    try:
        conn = get_db()
        cur = conn.cursor()
        
        print("📦 Creating database tables...")
        
        # Users table (sellers/buyers)
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
        print("✅ users table created")
        
        # Listings table (main marketplace)
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
        print("✅ listings table created")
        
        # Admins table (trusted admin list)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                telegram_username VARCHAR(255) UNIQUE NOT NULL,
                profile_picture TEXT,
                payment_method TEXT,
                is_super_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ admins table created")
        
        # Special skills table (admin editable)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id SERIAL PRIMARY KEY,
                skill_name VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ skills table created")
        
        # Insert default skills
        default_skills = [
            'Low Screamer', 'Phenomenal Finishing', 'Blitz Curler', 'Edge Crossing',
            'Visionary Pass', 'Phenomenal Pass', 'Aerial Fort', 'Long Reach Tackle',
            'Fortress', 'Acceleration Burst', 'Momentum Dribbling', 'Magnetic Fit',
            'GK Directing Defense', 'GK Sprint Roar', 'Willpower', 'Bullet Header',
            'Game-Changing Pass', 'Attack Trigger'
        ]
        
        for skill in default_skills:
            cur.execute("""
                INSERT INTO skills (skill_name) VALUES (%s)
                ON CONFLICT (skill_name) DO NOTHING
            """, (skill,))
        
        # Insert default admins
        cur.execute("""
            INSERT INTO users (telegram_username, pin, is_admin, admin_role) 
            VALUES (%s, %s, TRUE, 'owner') 
            ON CONFLICT (telegram_username) DO NOTHING
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

@app.route('/login')
def login():
    return send_from_directory('.', 'login.html')

# Test route
@app.route('/api/test')
def test():
    return jsonify({'status': 'Marketplace is running!', 'database': 'connected'})

# ==================== USER ENDPOINTS ====================

# Register/Login user
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.json
        telegram_username = data.get('telegram_username', '')
        pin = data.get('pin', '')
        
        if not telegram_username or not pin:
            return jsonify({'success': False, 'message': 'Username and PIN required'})
        
        if len(pin) < 4 or len(pin) > 6:
            return jsonify({'success': False, 'message': 'PIN must be 4-6 digits'})
        
        if not telegram_username.startswith('@'):
            telegram_username = '@' + telegram_username
        
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("SELECT id, is_admin, is_banned FROM users WHERE telegram_username = %s", (telegram_username,))
        user = cur.fetchone()
        
        if not user:
            cur.execute("""
                INSERT INTO users (telegram_username, pin) 
                VALUES (%s, %s) RETURNING id, is_admin, is_banned
            """, (telegram_username, pin))
            user = cur.fetchone()
            user_id = user[0]
            is_admin = user[1]
            is_banned = user[2]
        else:
            user_id = user[0]
            is_admin = user[1]
            is_banned = user[2]
            # Check PIN (in real app, you'd verify here)
        
        conn.commit()
        cur.close()
        conn.close()
        
        if is_banned:
            return jsonify({'success': False, 'message': 'You are banned'})
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'is_admin': is_admin,
            'username': telegram_username
        })
        
    except Exception as e:
        print(f"❌ Register error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== LISTINGS ENDPOINTS ====================

# Get all active listings (for main feed)
@app.route('/api/listings', methods=['GET'])
def get_listings():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cur.execute("""
            SELECT * FROM listings 
            WHERE is_active = TRUE AND is_sold = FALSE 
            ORDER BY created_at DESC
        """)
        listings = cur.fetchall()
        
        result = []
        for l in listings:
            # Parse featured players from JSON or comma-separated
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
                'featured_players': featured[:4],  # Max 4
                'special_skills': skills,
                'created': l['created_at'].isoformat() if l['created_at'] else None
            })
        
        cur.close()
        conn.close()
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Listings error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# Get single listing detail
@app.route('/api/listing/<int:listing_id>', methods=['GET'])
def get_listing(listing_id):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cur.execute("""
            SELECT * FROM listings 
            WHERE id = %s AND is_active = TRUE
        """, (listing_id,))
        listing = cur.fetchone()
        
        if not listing:
            return jsonify({'success': False, 'message': 'Listing not found'}), 404
        
        # Get all admins for trusted list
        cur.execute("SELECT * FROM admins ORDER BY name")
        admins = cur.fetchall()
        
        admin_list = []
        for a in admins:
            admin_list.append({
                'name': a['name'],
                'telegram': a['telegram_username'],
                'profile_pic': a['profile_picture'],
                'payment': a['payment_method']
            })
        
        # Parse featured players and skills
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
        print(f"❌ Listing detail error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# Create new listing (seller post)
@app.route('/api/create_listing', methods=['POST'])
def create_listing():
    try:
        data = request.json
        seller = data.get('seller_username')
        main_screenshot = data.get('main_screenshot')
        overbench_screenshot = data.get('overbench_screenshot')
        price = data.get('price')
        featured_players = data.get('featured_players', [])
        special_skills = data.get('special_skills', [])
        coin_amount = data.get('coin_amount', 0)
        trade_type = data.get('trade_type', 'FOR SALE')
        link_type = data.get('link_type', 'KONAMI LINK')
        
        if not all([seller, main_screenshot, overbench_screenshot, price]):
            return jsonify({'success': False, 'message': 'Missing required fields'})
        
        # Check for duplicate screenshots (simplified - you'd compare image hashes)
        # This is a placeholder for duplicate detection
        
        conn = get_db()
        cur = conn.cursor()
        
        # Convert arrays to comma-separated strings
        featured_str = ','.join(featured_players[:4])  # Max 4
        skills_str = ','.join(special_skills)
        
        cur.execute("""
            INSERT INTO listings 
            (seller_username, main_squad_screenshot, overbench_screenshot, price, 
             featured_players, special_skills, coin_amount, trade_type, link_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (seller, main_screenshot, overbench_screenshot, price, 
              featured_str, skills_str, coin_amount, trade_type, link_type))
        
        listing_id = cur.fetchone()[0]
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'listing_id': listing_id})
        
    except Exception as e:
        print(f"❌ Create listing error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== SKILLS ENDPOINTS ====================

# Get all skills (for seller form)
@app.route('/api/skills', methods=['GET'])
def get_skills():
    try:
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("SELECT skill_name FROM skills ORDER BY skill_name")
        skills = cur.fetchall()
        
        result = [s[0] for s in skills]
        
        cur.close()
        conn.close()
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Skills error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== ADMIN ENDPOINTS ====================

# Admin login
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if username == OWNER_USERNAME and password == '12604':
            return jsonify({'success': True, 'role': 'owner', 'username': username})
        elif username == ADMIN_USERNAME and password == '11512':
            return jsonify({'success': True, 'role': 'admin', 'username': username})
        else:
            return jsonify({'success': False, 'message': 'Invalid credentials'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Get all listings (admin view)
@app.route('/api/admin/listings', methods=['GET'])
def admin_listings():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cur.execute("""
            SELECT * FROM listings 
            ORDER BY created_at DESC
        """)
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
        return jsonify({'success': False, 'message': str(e)}), 500

# Edit listing (admin)
@app.route('/api/admin/edit_listing', methods=['POST'])
def edit_listing():
    try:
        data = request.json
        listing_id = data.get('listing_id')
        price = data.get('price')
        coin_amount = data.get('coin_amount')
        trade_type = data.get('trade_type')
        link_type = data.get('link_type')
        is_active = data.get('is_active')
        is_sold = data.get('is_sold')
        
        conn = get_db()
        cur = conn.cursor()
        
        updates = []
        params = []
        
        if price is not None:
            updates.append("price = %s")
            params.append(price)
        if coin_amount is not None:
            updates.append("coin_amount = %s")
            params.append(coin_amount)
        if trade_type:
            updates.append("trade_type = %s")
            params.append(trade_type)
        if link_type:
            updates.append("link_type = %s")
            params.append(link_type)
        if is_active is not None:
            updates.append("is_active = %s")
            params.append(is_active)
        if is_sold is not None:
            updates.append("is_sold = %s")
            params.append(is_sold)
        
        if updates:
            query = f"UPDATE listings SET {', '.join(updates)} WHERE id = %s"
            params.append(listing_id)
            cur.execute(query, params)
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Delete listing (admin)
@app.route('/api/admin/delete_listing', methods=['POST'])
def delete_listing():
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

# Admin skills management
@app.route('/api/admin/skills', methods=['POST', 'PUT', 'DELETE'])
def manage_skills():
    try:
        data = request.json
        action = data.get('action')  # 'add', 'edit', 'delete'
        skill_name = data.get('skill_name')
        new_name = data.get('new_name')
        
        conn = get_db()
        cur = conn.cursor()
        
        if action == 'add':
            cur.execute("INSERT INTO skills (skill_name) VALUES (%s)", (skill_name,))
        elif action == 'edit':
            cur.execute("UPDATE skills SET skill_name = %s WHERE skill_name = %s", (new_name, skill_name))
        elif action == 'delete':
            cur.execute("DELETE FROM skills WHERE skill_name = %s", (skill_name,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Initialize database on startup
print("🚀 Initializing database...")
init_db()

if __name__ == '__main__':
    try:
        port = int(os.environ.get('PORT', 5000))
        print(f"🚀 Server starting on port {port}")
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
