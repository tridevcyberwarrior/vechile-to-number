import json
import requests
import os
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

JSON_URL = os.environ.get('JSON_URL', 'https://huggingface.co/buckets/tridevcyber/vechile-to-number/resolve/vehicleinfo.json?download=true')

CREDIT = {
    "developer": "tridevcyber",
    "hosted_on": "Vercel",
    "version": "2.0",
    "data_source": "Hugging Face Bucket"
}

# Simple in-memory cache (works for warm functions)
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
        print(f"Loaded {len(data)} records")
        return data
        
    except Exception as e:
        print(f"Error loading data: {e}")
        return []

def handler(request):
    """Vercel serverless handler"""
    path = request.get('path', '/')
    method = request.get('method', 'GET')
    
    # Parse query params
    query_string = request.get('query', {})
    
    # Home route
    if path == '/' or path == '':
        data = get_data()
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "status": "Vehicle to Phone API - Open Access",
                "credit": CREDIT,
                "total_records": len(data),
                "endpoints": {
                    "/vehicle/<rc>": "Get phone by vehicle number",
                    "/search?q=XX": "Search vehicles",
                    "/random": "Get random record",
                    "/stats": "API statistics"
                },
                "example": "/vehicle/PB65BE0037"
            })
        }
    
    # Vehicle lookup
    if path.startswith('/vehicle/'):
        rc_number = path.replace('/vehicle/', '').upper().replace(" ", "")
        data = get_data()
        
        result = None
        for item in data:
            v_rc = str(item.get('rc', '')).upper().replace(" ", "")
            if v_rc == rc_number:
                result = item
                break
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": True,
                "credit": "tridevcyber",
                "vehicle_rc": rc_number,
                "found": result is not None,
                "data": {
                    "vehicle_number": result['rc'] if result else None,
                    "phone": result['m'] if result else None
                } if result else None
            })
        }
    
    # Search route
    if path == '/search':
        query = query_string.get('q', [''])[0].upper()
        if not query:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Query parameter 'q' required"})
            }
        
        data = get_data()
        results = []
        
        for item in data:
            v_rc = str(item.get('rc', '')).upper()
            if query in v_rc:
                results.append({
                    "vehicle_number": item.get('rc'),
                    "phone": item.get('m')
                })
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": True,
                "credit": "tridevcyber",
                "query": query,
                "total_results": len(results),
                "results": results[:50]
            })
        }
    
    # Random route
    if path == '/random':
        import random
        data = get_data()
        
        if not data:
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "No data"})
            }
        
        item = random.choice(data)
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": True,
                "credit": "tridevcyber",
                "data": {
                    "vehicle_number": item.get('rc'),
                    "phone": item.get('m')
                }
            })
        }
    
    # Stats route
    if path == '/stats':
        data = get_data()
        if not data:
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Data unavailable"})
            }
        
        # Count by state
        states = {}
        for item in data:
            rc = item.get('rc', '')
            if len(rc) >= 2:
                state = rc[:2]
                states[state] = states.get(state, 0) + 1
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": True,
                "credit": "tridevcyber",
                "total_records": len(data),
                "states_count": len(states),
                "top_states": dict(sorted(states.items(), key=lambda x: x[1], reverse=True)[:10])
            })
        }
    
    # 404 for unknown routes
    return {
        "statusCode": 404,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": "Not found"})
    }

class VercelHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Parse request
        parsed = urlparse(self.path)
        
        request_data = {
            'path': parsed.path,
            'method': 'GET',
            'query': parse_qs(parsed.query)
        }
        
        # Call handler
        response = handler(request_data)
        
        # Send response
        self.send_response(response['statusCode'])
        for header, value in response.get('headers', {}).items():
            self.send_header(header, value)
        self.end_headers()
        self.wfile.write(response['body'].encode())

# Vercel entry point
def main(request):
    """Vercel serverless function entry point"""
    from urllib.parse import urlparse, parse_qs
    
    parsed = urlparse(request.url)
    query = parse_qs(parsed.query)
    
    request_data = {
        'path': parsed.path,
        'method': request.method,
        'query': query
    }
    
    response = handler(request_data)
    
    return response
