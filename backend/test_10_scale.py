"""Test the 0-10 rating system"""
import requests

LOCAL = "http://localhost:8000"

print("=== TESTING 0-10 RATING SYSTEM ===")

# Test rating submission with 0-10
test_payload = {"User_id": 41, "Movie_id": 88, "Score": 5}
print(f"Submitting: {test_payload}")

r = requests.post(f"{LOCAL}/ratings", json=test_payload)
print(f"Status: {r.status_code} Response: {r.json()}")

# Check what's saved
r2 = requests.get(f"{LOCAL}/users/41/history")
for h in r2.json():
    if h['Movie_id'] == 88:
        print(f"History shows: {h['Title']} User_Rating={h.get('User_Rating')}")
