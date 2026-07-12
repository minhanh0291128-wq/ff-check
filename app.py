from flask import Flask, render_template, jsonify, request
import requests
from datetime import datetime, timezone

app = Flask(__name__)

# --- siambhau API (primary) ---
SIAMBHAU_KEY = 'FFINFO-Free'
SIAMBHAU_BASE = 'https://siambhau69.eu.cc/freefireinfo/bhau'
SIAMBHAU_REGIONS = ['BD', 'IND']

# --- HL Gaming API (fallback) ---
HL_KEY = '7vB9oJCF7II1PY8oidpcUpWSOAKizw'
HL_UID = 'OGkM1WzgzXbqLLovkBJFXWfNX2h1'
HL_BASE = 'https://proapis.hlgamingofficial.com/main/games/freefire/account/api'

REGIONS = ['SG', 'IND', 'BD', 'ID', 'TH', 'TW', 'VN', 'BR', 'US', 'EU', 'NP', 'ME', 'RU', 'PK']

@app.after_request
def add_headers(resp):
    resp.headers['ngrok-skip-browser-warning'] = '1'
    return resp

def detect_region(uid):
    return REGIONS[int(uid[0]) % len(REGIONS)] if uid and uid[0].isdigit() else 'SG'

def parse_siambhau(data):
    result = data.get('result') or data
    basic = result.get('basicInfo', {}) or {}
    clan = result.get('clanBasicInfo', {}) or {}

    if not basic.get('nickname'):
        return None

    last_login = int(basic.get('lastLoginAt', 0)) if str(basic.get('lastLoginAt', '0')).isdigit() else 0
    created = int(basic.get('createAt', 0)) if str(basic.get('createAt', '0')).isdigit() else 0
    now = datetime.now(timezone.utc).timestamp()

    diff = now - last_login
    is_online = 0 < diff < 900 if last_login else False

    return {
        'nickname': basic.get('nickname', 'Không rõ'),
        'level': basic.get('level', 0),
        'liked': basic.get('liked', 0),
        'guild': clan.get('clanName', 'Không có'),
        'region': basic.get('region', 'BD'),
        'online': is_online,
        'lastLoginAt': last_login,
        'createAt': created,
        'accountAge': datetime.fromtimestamp(created).strftime('%d/%m/%Y') if created else 'Không rõ'
    }

def parse_hl_gaming(data):
    result = data.get('result', {})
    account = result.get('AccountInfo', {}) or {}
    info = result.get('captainBasicInfo', {}) or {}
    guild = result.get('GuildInfo', {}) or {}

    nickname = account.get('AccountName') or info.get('nickname', 'Không rõ')
    if not nickname or nickname == 'Không rõ':
        return None

    level = account.get('AccountLevel') or info.get('level', 0)
    liked = account.get('AccountLikes') or info.get('liked', 0)
    region_name = account.get('AccountRegion') or info.get('region', 'SG')

    last_login = account.get('AccountLastLogin') or info.get('lastLoginAt', 0)
    created = account.get('AccountCreateTime') or info.get('createAt', 0)

    if isinstance(last_login, str):
        try: last_login = int(last_login)
        except: last_login = 0
    if isinstance(created, str):
        try: created = int(created)
        except: created = 0

    now = datetime.now(timezone.utc).timestamp()

    diff = now - last_login
    is_online = 0 < diff < 900 if last_login else False

    return {
        'nickname': nickname,
        'level': level,
        'liked': liked,
        'guild': guild.get('GuildName', 'Không có'),
        'region': region_name,
        'online': is_online,
        'lastLoginAt': last_login,
        'createAt': created,
        'accountAge': datetime.fromtimestamp(created).strftime('%d/%m/%Y') if created else 'Không rõ'
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/check')
def api_check():
    uid = request.args.get('uid', '').strip()
    if not uid or len(uid) < 6 or not uid.isdigit():
        return jsonify({'error': 'UID không hợp lệ'}), 400

    # Try siambhau API first
    for region in SIAMBHAU_REGIONS:
        try:
            resp = requests.get(SIAMBHAU_BASE, params={
                'uid': uid, 'region': region, 'key': SIAMBHAU_KEY
            }, timeout=10)

            if resp.status_code != 200:
                continue

            data = resp.json()
            if data and not data.get('error'):
                parsed = parse_siambhau(data)
                if parsed:
                    return jsonify(parsed)
        except requests.exceptions.RequestException:
            continue

    # Fallback: HL Gaming API
    first = detect_region(uid)
    for region in [first] + [r for r in REGIONS if r != first]:
        try:
            resp = requests.get(HL_BASE, params={
                'sectionName': 'AllData',
                'PlayerUid': uid,
                'region': region,
                'useruid': HL_UID,
                'api': HL_KEY
            }, timeout=10)

            data = resp.json()

            if data.get('status') == 'quota_exceeded':
                return jsonify({'error': 'API hết lượt, mai thử lại nhé (25/25)'}), 429
            if data.get('error_code'):
                continue
            if resp.status_code != 200:
                continue

            if data and 'result' in data:
                parsed = parse_hl_gaming(data)
                if parsed:
                    return jsonify(parsed)
        except requests.exceptions.RequestException:
            continue

    return jsonify({'error': 'Không tìm thấy UID'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
