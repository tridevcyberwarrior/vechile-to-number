from flask import Flask, jsonify, request
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# Credit
CREDIT = {
    "developer": "tridevcyber",
    "bucket": "vechile-to-number",
    "version": "1.0",
    "description": "Vehicle Number to Phone Number Lookup API"
}

# Hugging Face Bucket URL
JSON_URL = "https://huggingface.co/buckets/tridevcyber/vechile-to-number/resolve/vehicleinfo.json?download=true"

# Cache data (optional - performance ke liye)
cached_data = None

def get_data():
    """Fetch data from Hugging Face Bucket"""
    global cached_data
    if cached_data is None:
        try:
            response = requests.get(JSON_URL, timeout=30)
            response.raise_for_status()
            cached_data = response.json()
        except Exception as e:
            return None, str(e)
    return cached_data, None

@app.route('/')
def home():
    """Home endpoint with API info"""
    return jsonify({
        "status": "API is running!",
        "credit": CREDIT,
        "endpoints": {
            "/": "API info",
            "/data": "Get all data",
            "/search": "Search by vehicle number (query: q)",
            "/vehicle/<number>": "Get phone by vehicle number",
            "/stats": "Data statistics"
        },
        "example": "/vehicle/DL8CAF1234"
    })

@app.route('/credit')
def credit():
    """Developer credit"""
    return jsonify({
        "developed_by": "tridevcyber",
        "message": "Made with ❤️ by tridevcyber",
        "bucket_url": "https://huggingface.co/buckets/tridevcyber/vechile-to-number"
    })

@app.route('/data', methods=['GET'])
def get_all_data():
    """Get all vehicle data"""
    data, error = get_data()
    if error:
        return jsonify({
            "success": False,
            "error": error,
            "credit": CREDIT
        }), 500
    
    # Limit response size
    total = len(data) if isinstance(data, list) else 1
    return jsonify({
        "success": True,
        "total_records": total,
        "credit": CREDIT,
        "data": data[:50] if isinstance(data, list) and total > 50 else data  # First 50 records
    })

@app.route('/vehicle/<vehicle_number>', methods=['GET'])
def get_by_vehicle(vehicle_number):
    """Get phone number by vehicle number"""
    data, error = get_data()
    if error:
        return jsonify({
            "success": False,
            "error": error,
            "credit": CREDIT
        }), 500
    
    # Search for vehicle
    vehicle_number = vehicle_number.upper().replace(" ", "")
    result = None
    
    if isinstance(data, list):
        for item in data:
            # Different possible keys check karo
            v_num = str(item.get('vehicle_number', item.get('vehicle', item.get('number', '')))).upper().replace(" ", "")
            if v_num == vehicle_number:
                result = item
                break
    
    if result:
        return jsonify({
            "success": True,
            "credit": CREDIT,
            "vehicle_number": vehicle_number,
            "found": True,
            "data": result
        })
    else:
        return jsonify({
            "success": True,
            "credit": CREDIT,
            "vehicle_number": vehicle_number,
            "found": False,
            "message": "Vehicle number not found"
        }), 404

@app.route('/search', methods=['GET'])
def search():
    """Search vehicle by partial number"""
    query = request.args.get('q', '').upper().replace(" ", "")
    if not query:
        return jsonify({
            "success": False,
            "error": "Query parameter 'q' is required",
            "credit": CREDIT
        }), 400
    
    data, error = get_data()
    if error:
        return jsonify({
            "success": False,
            "error": error,
            "credit": CREDIT
        }), 500
    
    results = []
    if isinstance(data, list):
        for item in data:
            v_num = str(item.get('vehicle_number', item.get('vehicle', item.get('number', '')))).upper()
            if query in v_num:
                results.append(item)
    
    return jsonify({
        "success": True,
        "credit": CREDIT,
        "query": query,
        "total_results": len(results),
        "results": results[:20]  # Max 20 results
    })

@app.route('/stats', methods=['GET'])
def stats():
    """Get data statistics"""
    data, error = get_data()
    if error:
        return jsonify({
            "success": False,
            "error": error,
            "credit": CREDIT
        }), 500
    
    if isinstance(data, list):
        total = len(data)
        # Sample first record to show structure
        sample = data[0] if total > 0 else None
        keys = list(sample.keys()) if sample else []
        
        return jsonify({
            "success": True,
            "credit": CREDIT,
            "total_records": total,
            "available_fields": keys,
            "sample_record": sample
        })
    else:
        return jsonify({
            "success": True,
            "credit": CREDIT,
            "data_type": type(data).__name__
        })

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "success": False,
        "error": "Endpoint not found",
        "credit": CREDIT,
        "available_endpoints": ["/", "/data", "/search", "/vehicle/<number>", "/stats", "/credit"]
    }), 404

if __name__ == '__main__':
    print(f"🚗 Vehicle to Phone API by tridevcyber")
    print(f"📊 Loading data from: {JSON_URL}")
    app.run(debug=True, host='0.0.0.0', port=5000)
