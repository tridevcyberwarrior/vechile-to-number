from flask import Flask, jsonify, request
import json
import requests
import os

app = Flask(__name__)

JSON_URL = os.environ.get('JSON_URL', 'https://huggingface.co/buckets/tridevcyber/vechile-to-number/resolve/vehicleinfo.json?download=true')

CREDIT = {
    "developer": "tridevcyber",
    "hosted_on": "Vercel",
    "version": "2.0",
    "data_source": "Hugging Face Bucket"
}

_data_cache = None

def get_data():
    """Parse NDJSON format"""
    global _data_cache
    if _data_cache is not None:
        return _data_cache
    
    try:
        response = requests.get(JSON_URL, timeout=30)
        text = response.text.strip()
        
        data = []
        for line in text.split('\n'):
            line = line.strip()
            if line:
                try:
                    obj = json.loads(line)
                    data.append(obj)
                except:
                    continue
        
        _data_cache = data
        return data
    except Exception as e:
        print(f"Error: {e}")
        return []

@app.route('/')
def home():
    return jsonify({
        "status": "Vehicle to Phone API - Open Access",
        "credit": CREDIT,
        "total_records": len(get_data()),
        "endpoints": {
            "/vehicle/<rc>": "Get phone by vehicle number",
            "/search?q=XX": "Search vehicles",
            "/random": "Get random record",
            "/stats": "API statistics"
        }
    })

@app.route('/vehicle/<rc_number>')
def get_vehicle(rc_number):
    data = get_data()
    rc_number = rc_number.upper().replace(" ", "")
    
    for item in data:
        v_rc = str(item.get('rc', '')).upper().replace(" ", "")
        if v_rc == rc_number:
            return jsonify({
                "success": True,
                "found": True,
                "data": {
                    "vehicle_number": item['rc'],
                    "phone": item['m']
                }
            })
    
    return jsonify({
        "success": True,
        "found": False,
        "data": None
    })

@app.route('/search')
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
        "query": query,
        "total_results": len(results),
        "results": results[:50]
    })

@app.route('/random')
def random_vehicle():
    import random
    data = get_data()
    
    if not data:
        return jsonify({"error": "No data"}), 500
    
    item = random.choice(data)
    return jsonify({
        "success": True,
        "data": {
            "vehicle_number": item.get('rc'),
            "phone": item.get('m')
        }
    })

@app.route('/stats')
def stats():
    data = get_data()
    
    states = {}
    for item in data:
        rc = item.get('rc', '')
        if len(rc) >= 2:
            state = rc[:2]
            states[state] = states.get(state, 0) + 1
    
    return jsonify({
        "success": True,
        "total_records": len(data),
        "states_count": len(states),
        "top_states": dict(sorted(states.items(), key=lambda x: x[1], reverse=True)[:10])
    })
