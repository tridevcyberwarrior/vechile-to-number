
    import json
import requests
import os
from flask import Flask, jsonify, request

app = Flask(__name__)

JSON_URL = os.environ.get('JSON_URL', 'https://huggingface.co/buckets/tridevcyber/vechile-to-number/resolve/vehicleinfo.json?download=true')

CREDIT = {
    "developer": "tridevcyber",
    "hosted_on": "Vercel",
    "version": "2.0",
    "data_source": "Hugging Face Bucket"
}

cached_data = None

def get_data():
    """Parse NDJSON format"""
    global cached_data
    if cached_data is None:
        try:
            response = requests.get(JSON_URL, timeout=30)
            text = response.text.strip()
            
            cached_data = []
            for line in text.split('\n'):
                line = line.strip()
                if line:
                    try:
                        obj = json.loads(line)
                        cached_data.append(obj)
                    except:
                        continue
            
            print(f"Loaded {len(cached_data)} records")
            
        except Exception as e:
            print(f"Error: {e}")
            return None
    return cached_data

@app.route('/')
def home():
    return jsonify({
        "status": "Vehicle to Phone API - Open Access",
        "credit": CREDIT,
        "total_records": len(get_data()) if get_data() else 0,
        "endpoints": {
            "/vehicle/<rc>": "Get phone by vehicle number",
            "/search?q=XX": "Search vehicles",
            "/random": "Get random record",
            "/stats": "API statistics"
        },
        "example": "/vehicle/PB65BE0037"
    })

@app.route('/vehicle/<rc_number>')
def get_vehicle(rc_number):
    data = get_data()
    if not data:
        return jsonify({"error": "Data unavailable"}), 500
    
    rc_number = rc_number.upper().replace(" ", "")
    result = None
    
    for item in data:
        v_rc = str(item.get('rc', '')).upper().replace(" ", "")
        if v_rc == rc_number:
            result = item
            break
    
    return jsonify({
        "success": True,
        "credit": "tridevcyber",
        "vehicle_rc": rc_number,
        "found": result is not None,
        "data": {
            "vehicle_number": result['rc'] if result else None,
            "phone": result['m'] if result else None
        } if result else None
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
        "credit": "tridevcyber",
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
        "credit": "tridevcyber",
        "data": {
            "vehicle_number": item.get('rc'),
            "phone": item.get('m')
        }
    })

@app.route('/stats')
def stats():
    data = get_data()
    if not data:
        return jsonify({"error": "Data unavailable"}), 500
    
    # Count by state
    states = {}
    for item in data:
        rc = item.get('rc', '')
        if len(rc) >= 2:
            state = rc[:2]
            states[state] = states.get(state, 0) + 1
    
    return jsonify({
        "success": True,
        "credit": "tridevcyber",
        "total_records": len(data),
        "states_count": len(states),
        "top_states": dict(sorted(states.items(), key=lambda x: x[1], reverse=True)[:10])
    })

if __name__ == '__main__':
    app.run(debug=True)
