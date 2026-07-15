from flask import Flask, render_template, jsonify, request
import requests
from datetime import datetime

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
    social = result.get('socialInfo', {}) or {}
    profile = result.get('profileInfo', {}) or {}
    pet = result.get('petInfo', {}) or {}

    if not basic.get('nickname'):
        return None

    last_login = int(basic.get('lastLoginAt', 0)) if str(basic.get('lastLoginAt', '0')).isdigit() else 0
    created = int(basic.get('createAt', 0)) if str(basic.get('createAt', '0')).isdigit() else 0

    gender_map = {'Gender_FEMALE': 'Nữ', 'Gender_MALE': 'Nam'}
    lang_map = {'Language_VIETNAMESE': 'Tiếng Việt', 'Language_ENGLISH': 'English', 'Language_INDONESIAN': 'Bahasa', 'Language_HINDI': 'हिन्दी'}

    return {
        'nickname': basic.get('nickname', 'Không rõ'),
        'level': basic.get('level', 0),
        'liked': basic.get('liked', 0),
        'guild': clan.get('clanName', 'Không có'),
        'guildLevel': clan.get('clanLevel', 0),
        'guildMembers': f"{clan.get('memberNum', 0)}/{clan.get('capacity', 0)}",
        'region': basic.get('region', 'BD'),
        'signature': social.get('signature', ''),
        'gender': gender_map.get(social.get('gender', ''), ''),
        'language': lang_map.get(social.get('language', ''), social.get('language', '')),
        'primeLevel': basic.get('primeInfo', {}).get('primeLevel', 0),
        'badgeCnt': basic.get('badgeCnt', 0),
        'releaseVersion': basic.get('releaseVersion', ''),
        'headPic': basic.get('headPic', 0),
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

    return {
        'nickname': nickname,
        'level': level,
        'liked': liked,
        'guild': guild.get('GuildName', 'Không có'),
        'guildLevel': guild.get('GuildLevel', 0),
        'guildMembers': f"{guild.get('GuildMember', 0)}/{guild.get('GuildCapacity', 0)}",
        'region': region_name,
        'signature': '',
        'gender': '',
        'language': '',
        'primeLevel': 0,
        'badgeCnt': info.get('badgeCnt', 0),
        'releaseVersion': info.get('releaseVersion', ''),
        'headPic': info.get('headPic', 0),
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
            if data:
                if data.get('error'):
                    return jsonify({'error': data['error']}), 400
                parsed = parse_siambhau(data)
                if parsed:
                    return jsonify(parsed)
                return jsonify({'error': 'API không tìm thấy UID này'}), 404
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

@app.route('/api/tiktok')
def api_tiktok():
    username = request.args.get('username', '').strip().lstrip('@')
    if not username or len(username) < 2:
        return jsonify({'error': 'Username không hợp lệ'}), 400

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        resp = requests.get(f'https://www.tiktok.com/@{username}', headers=headers, timeout=15)
        if resp.status_code != 200:
            return jsonify({'error': 'Không tìm thấy username này'}), 404

        import re
        m = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>([^<]+)</script>', resp.text)
        if not m:
            return jsonify({'error': 'Không thể lấy dữ liệu TikTok'}), 502

        import json
        data = json.loads(m.group(1))
        scope = data.get('__DEFAULT_SCOPE__', {})
        user_info = scope.get('webapp.user-detail', {}).get('userInfo', {})
        user = user_info.get('user', {})
        stats = user_info.get('stats', {})

        if not user:
            return jsonify({'error': 'Không tìm thấy người dùng'}), 404

        fmt = lambda n: n // 1000000 and f'{n/1000000:.1f}M' or n // 1000 and f'{n//1000}k' or str(n)

        created = user.get('createTime', 0)
        bio_link = user.get('bioLink', {}).get('link', '') if user.get('bioLink') else ''

        return jsonify({
            'username': username,
            'displayName': user.get('nickname', ''),
            'avatar': user.get('avatarLarger', ''),
            'bio': user.get('signature', ''),
            'bioLink': bio_link,
            'followers': stats.get('followerCount', 0),
            'following': stats.get('followingCount', 0),
            'likes': stats.get('heartCount', 0),
            'videos': stats.get('videoCount', 0),
            'verified': user.get('verified', False),
            'private': user.get('privateAccount', False),
            'accountAge': datetime.fromtimestamp(created).strftime('%d/%m/%Y') if created else '',
            'followersFmt': fmt(stats.get('followerCount', 0)),
            'followingFmt': fmt(stats.get('followingCount', 0)),
            'likesFmt': fmt(stats.get('heartCount', 0)),
            'videosFmt': fmt(stats.get('videoCount', 0)),
        })
    except requests.exceptions.RequestException:
        return jsonify({'error': 'Lỗi kết nối TikTok'}), 502

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
