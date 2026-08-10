import urllib.request
import json

try:
    url = "http://127.0.0.1:4040/api/requests/http?limit=50"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        requests = data.get("requests", [])
        print(f"Total ngrok requests fetched: {len(requests)}")
        for r in requests:
            uri = r.get("uri")
            method = r.get("request", {}).get("method")
            status = r.get("response", {}).get("status_code") if r.get("response") else "No Response"
            start = r.get("start")
            duration = r.get("duration")
            print(f"[{start}] {method} {uri} -> Status: {status} (duration: {duration}ns)")
except Exception as e:
    print(f"Error querying ngrok API: {e}")
