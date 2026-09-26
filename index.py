
    import json
import requests
import os
from flask import Flask, jsonify, request
from functools import wraps
import time

app = Flask(__name__)

ADMIN_KEY = os.environ.get('ADMIN_KEY', 'tridevcyber_admin_2024')
JSON_URL = os.environ.get('JSON_URL', 'https://huggingface.co/buckets/tridevcyber/vechile-to-number/resolve/vehicleinfo.json?download=true')

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import db

CREDIT = {
    "developer": "tridevcyber",
    "hosted_on": "Vercel",
    "version": "2.0"
}

cached_data = None
request_history = {}

def get_data():
    """Parse NDJSON format (one JSON object per line)"""
    global cached_data
    if cached_data is None:
        try:
            response = requests.get(JSON_URL, timeout=30)
            text = response.text.strip()
            
            # NDJSON parse: har line ko alag JSON object
            cached_data = []
            for line in text.split('\n'):
                line = line.strip()
                if line:  # Empty lines skip karo
                    try:
                        obj = json.loads(line)
                        cached_data.append(obj)
                    except json.JSONDecodeError:
                        continue  # Invalid line skip karo
            
            print(f"Loaded {len(cached_data)} records")
            
        except Exception as e:
            print(f"Error: {e}")
            return None
    return cached_data

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            return jsonify({
                "success": False,
                "error": "API key required",
                "contact": "tridevcyber"
            }), 401
        
        key_data = db.validate_key(api_key)
        if not key_data:
            return jsonify({
                "success": False,
                "error": "Invalid API key"
            }), 401
        
        if key_data['requests_today'] >= key_data['daily_limit']:
            return jsonify({
                "success": False,
                "error": "Daily limit exceeded",
                "plan": key_data['plan']
            }), 429
        
        # Rate limit
        current_time = time.time()
        if api_key not in request_history:
            request_history[api_key] = []
        
        request_history[api_key] = [t for t in request_history[api_key] if current_time - t < 60]
        
        if len(request_history[api_key]) >= key_data['rate_limit']:
            return jsonify({"error": "Rate limit exceeded"}), 429
        
        request_history[api_key].append(current_time)
        db.increment_usage(api_key, request.endpoint)
        request.key_data = key_data
        
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.headers.get('X-Admin-Key') != ADMIN_KEY:
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def home():
    return jsonify({
        "status": "Vehicle to Phone API",
        "credit": CREDIT,
        "data_format": "rc=Vehicle Number, m=Mobile",
        "endpoints": ["/vehicle/<rc>", "/search", "/plans"]
    })

@app.route('/vehicle/<rc_number>')
@require_api_key
def get_vehicle(rc_number):
    data = get_data()
    if not data:
        return jsonify({"error": "Data unavailable"}), 500
    
    rc_number = rc_number.upper().replace(" ", "")
    result = None
    
    # Search by 'rc' key
    for item in data:
        v_rc = str(item.get('rc', '')).upper().replace(" ", "")
        if v_rc == rc_number:
            result = item
            break
    
    return jsonify({
        "success": True,
        "credit": "tridevcyber",
        "plan": request.key_data['plan'],
        "vehicle_rc": rc_number,
        "found": result is not None,
        "data": {
            "vehicle_number": result['rc'] if result else None,
            "phone": result['m'] if result else None,
            "raw": result
        } if result else None
    })

@app.route('/search')
@require_api_key
def search():
    query = request.args.get('q', '').upper()
    if not query:
        return jsonify({"error": "Query parameter 'q' required"}), 400
    
    data = get_data()
    results = []
    
    for item in data:
        v_rc = str(item.get('rc', '')).upper()
        if query in v_rc:
            results.append({
                "vehicle_number": item.get('rc'),
                "phone": item.get('m')
            })
    
    return jsonify({
        "success": True,
        "credit": "tridevcyber",
        "query": query,
        "total_results": len(results),
        "results": results[:20]
    })

@app.route('/my-usage')
@require_api_key
def my_usage():
    return jsonify({
        "plan": request.key_data['plan'],
        "usage": {
            "today": request.key_data['requests_today'],
            "limit": request.key_data['daily_limit'],
            "remaining": request.key_data['daily_limit'] - request.key_data['requests_today']
        }
    })

@app.route('/plans')
def plans():
    return jsonify({
        "plans": {
            "free": {"price": "$0", "daily": 1000},
            "basic": {"price": "$10/month", "daily": 5000},
            "pro": {"price": "$30/month", "daily": 20000}
        }
    })

@app.route('/admin/create-key', methods=['POST'])
@admin_required
def create_key():
    data = request.get_json() or {}
    key = db.create_key(
        name=data.get('name', 'Unknown'),
        email=data.get('email', ''),
        plan=data.get('plan', 'free'),
        days=data.get('days', 30)
    )
    return jsonify({
        "success": True,
        "api_key": key,
        "plan": data.get('plan', 'free')
    })

@app.route('/admin/keys')
@admin_required
def list_keys():
    return jsonify({"keys": db.get_all_keys()})

if __name__ == '__main__':
    app.run(debug=True)
