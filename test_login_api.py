import requests

try:
    url = "http://localhost:8000/api/v1/auth/login"
    data = {
        "username": "shiva9532",
        "password": "#@112233"
    }
    r = requests.post(url, data=data)
    print("Status:", r.status_code)
    print("Headers:", r.headers)
    print("Content:", r.text)
except Exception as e:
    print("Error:", e)
