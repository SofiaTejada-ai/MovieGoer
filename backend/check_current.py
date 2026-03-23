import requests

print("=== CURRENT RATINGS FOR USER 53 ===")
r = requests.get("http://localhost:8000/users/53/history")
for h in r.json():
    print(f"{h['Title']:30} User_Rating={h.get('User_Rating')}")

print("\n=== CHECKING BACKEND LOGS FOR RATING REQUESTS ===")
# Check if any rating requests were logged
print("Look for 📊 Rating request: in backend console output")

print("\n=== TEST RATING SUBMISSION DIRECTLY ===")
# Test rating submission directly
test_payload = {"User_id": 53, "Movie_id": 21, "Score": 3}
r2 = requests.post("http://localhost:8000/ratings", json=test_payload)
print(f"Status: {r2.status_code}")
print(f"Response: {r2.json()}")

print("\n=== VERIFY SAVED ===")
r3 = requests.get("http://localhost:8000/users/53/history")
for h in r3.json():
    if h['Movie_id'] == 21:
        print(f"Forrest Gump now has User_Rating={h.get('User_Rating')}")
        break
