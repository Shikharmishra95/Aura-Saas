import urllib.request
import json
import base64

try:
    url = "http://127.0.0.1:4040/api/requests/http/airt_3Ha49MZcTjn9KwpEL6oIPEWCuPM"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print("=== REQUEST DETAILS ===")
        print(f"ID: {data.get('id')}")
        print(f"URI: {data.get('uri')}")
        print(f"Start: {data.get('start')}")
        print(f"Duration: {data.get('duration')}")
        
        request_details = data.get('request', {})
        print("\n=== REQUEST HEADERS ===")
        for k, v in request_details.get('headers', {}).items():
            print(f"  {k}: {v}")
            
        print("\n=== REQUEST RAW BODY ===")
        raw_body_b64 = request_details.get('raw')
        if raw_body_b64:
            try:
                print(base64.b64decode(raw_body_b64).decode())
            except Exception as body_err:
                print(f"Error decoding request body: {body_err}")
                
        response_details = data.get('response', {})
        if response_details:
            print("\n=== RESPONSE DETAILS ===")
            print(f"  Status: {response_details.get('status')}")
            print(f"  Status Code: {response_details.get('status_code')}")
            for k, v in response_details.get('headers', {}).items():
                print(f"    {k}: {v}")
            
            raw_resp_b64 = response_details.get('raw')
            if raw_resp_b64:
                try:
                    print(base64.b64decode(raw_resp_b64).decode('utf-8', errors='ignore'))
                except Exception as resp_err:
                    print(f"Error decoding response body: {resp_err}")
        else:
            print("\n=== NO RESPONSE ===")
except Exception as e:
    print(f"Error querying ngrok API: {e}")
