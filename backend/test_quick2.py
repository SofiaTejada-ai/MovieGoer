import requests

r = requests.get("http://localhost:8000/users/53/history")
print(f"Status: {r.status_code}")
print(f"Body: {r.text}")
