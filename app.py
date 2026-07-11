from flask import Flask, render_template, jsonify, request
import requests
from datetime import datetime, timezone

app = Flask(__name__)

API_KEY = '7vB9oJCF7II1PY8oidpcUpWSOAKizw'
API_UID = 'OGkM1WzgzXbqLLovkBJFXWfNX2h1'
API_BASE = 'https://proapis.hlgamingofficial.com/main/games/freefire/account/api'

REGIONS = ['SG', 'IND', 'BD', 'ID', 'TH', 'TW', 'VN', 'BR', 'US', 'EU', 'NP', 'ME', 'RU', 'PK']

@app.after_request
def add_headers(resp):
    resp.headers['ngrok-skip-browser-warning'] = '1'
    return resp

def detect_region(uid):
    return REGIONS[int(uid[0]) % len(REGIONS)] if uid and uid[0].isdigit() else 'SG'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/check')
def api_check():
    uid = request.args.get('uid', '').strip()
    if not uid or len(uid) < 6 or not uid.isdigit():
        return jsonify({'error': 'UID không hợp lệ'}), 400

    first = detect_region(uid)
    for region in [first] + [r for r in REGIONS if r != first]:
        try:
            resp = requests.get(API_BASE, params={
                'sectionName': 'AllData',
                'PlayerUid': uid,
                'region': region,
                'useruid': API_UID,
                'api': API_KEY
            }, timeout=10)

            if resp.status_code != 200:
                try:
                    err = resp.json()
                    if 'error' in err:
                        msg = err['error']
                        if 'quota' in msg.lower() or 'limit' in msg.lower():
                            return jsonify({'error': 'API hết lượt, thử lại sau'}), 429
                except:
                    pass
                continue

            data = resp.json()
            if data and 'result' in data:
                result = data['result']
                account = result.get('AccountInfo', {}) or {}
                info = result.get('captainBasicInfo', {}) or {}
                guild = result.get('GuildInfo', {}) or {}

                nickname = account.get('AccountName') or info.get('nickname', 'Không rõ')
                level = account.get('AccountLevel') or info.get('level', 0)
                liked = account.get('AccountLikes') or info.get('liked', 0)
                region_name = account.get('AccountRegion') or info.get('region', region)

                last_login = account.get('AccountLastLogin') or info.get('lastLoginAt', 0)
                created = account.get('AccountCreateTime') or info.get('createAt', 0)

                if isinstance(last_login, str):
                    try: last_login = int(last_login)
                    except: last_login = 0
                if isinstance(created, str):
                    try: created = int(created)
                    except: created = 0

                now = datetime.now(timezone.utc).timestamp()
                is_online = (now - last_login) < 900 if last_login else False

                return jsonify({
                    'nickname': nickname,
                    'level': level,
                    'liked': liked,
                    'guild': guild.get('GuildName', 'Không có'),
                    'region': region_name,
                    'online': is_online,
                    'lastLoginAt': last_login,
                    'createAt': created,
                    'accountAge': datetime.fromtimestamp(created).strftime('%d/%m/%Y') if created else 'Không rõ'
                })
        except requests.exceptions.RequestException:
            continue

    return jsonify({'error': 'Không tìm thấy UID'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
