from flask import Flask, render_template, jsonify, request
import requests
from datetime import datetime, timezone

app = Flask(__name__)

API_KEY = 'ffc_mr541c7x_sk7uci9jspurahyu091v'
API_BASE = 'https://developers.freefirecommunity.com/api/v1'

REGIONS = ['SG', 'IND', 'BD', 'SG', 'ID', 'TH', 'TW', 'VN', 'BR', 'US']

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
            resp = requests.get(f'{API_BASE}/info?region={region}&uid={uid}&key={API_KEY}', timeout=10)
            if resp.status_code != 200:
                try:
                    err = resp.json()
                    if 'QUOTA' in err.get('code', ''):
                        return jsonify({'error': 'API hết lượt, chờ đến 1/8/2026 hoặc dùng key mới'}), 429
                except: pass
                continue
            data = resp.json()
            if data and 'basicInfo' in data:
                info = data['basicInfo']
                clan = data.get('clanBasicInfo', {}) or {}

                last_login = info.get('lastLoginAt', 0)
                created = info.get('createAt', 0)
                now = datetime.now(timezone.utc).timestamp()

                is_online = (now - last_login) < 900 if last_login else False

                return jsonify({
                    'nickname': info.get('nickname', 'Không rõ'),
                    'level': info.get('level', 0),
                    'liked': info.get('liked', 0),
                    'guild': clan.get('clanName', 'Không có'),
                    'region': info.get('region', region),
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
