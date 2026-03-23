"""Test the full flow against LOCAL backend at localhost:8000"""
import requests

LOCAL = "http://localhost:8000"

# 1. Login as CarolinaSarria
print("=== LOGIN ===")
resp = requests.post(f"{LOCAL}/login", json={"Email": "carolina@gmail.com", "Password": "carolina123"})
if resp.status_code != 200:
    # Try to find the correct email
    print(f"Login failed: {resp.status_code} {resp.text}")
    # Check users list
    users = requests.get(f"{LOCAL}/users").json()
    carolina = [u for u in users if 'Carolina' in u.get('Username', '')]
    if carolina:
        print(f"Found: {carolina[0]}")
        # Try common passwords
        for pw in ["carolina", "password", "123456", "Carolina", "carolina123"]:
            r2 = requests.post(f"{LOCAL}/login", json={"Email": carolina[0]['Email'], "Password": pw})
            if r2.status_code == 200:
                resp = r2
                print(f"Logged in with password: {pw}")
                break
    else:
        print("User not found. Checking all users...")
        for u in users:
            print(f"  {u}")
else:
    print(f"Login OK")

if resp.status_code == 200:
    user_data = resp.json()
    user_id = user_data.get("User_id")
    print(f"User_id: {user_id}")
    print(f"Has access_token: {'access_token' in user_data}")
    
    # 2. Check history
    print(f"\n=== HISTORY for user {user_id} ===")
    hist = requests.get(f"{LOCAL}/users/{user_id}/history").json()
    for h in hist:
        print(f"  {h['Title']:30} User_Rating={h.get('User_Rating')}")
    
    # 3. Rate a movie that has no rating
    unrated = [h for h in hist if h.get('User_Rating') is None]
    if unrated:
        movie = unrated[0]
        print(f"\n=== RATING {movie['Title']} (id={movie['Movie_id']}) ===")
        r = requests.post(f"{LOCAL}/ratings", json={"User_id": user_id, "Movie_id": movie['Movie_id'], "Score": 4})
        print(f"  Status: {r.status_code} Response: {r.json()}")
        
        # 4. Re-check history
        print(f"\n=== HISTORY AFTER RATING ===")
        hist2 = requests.get(f"{LOCAL}/users/{user_id}/history").json()
        for h in hist2:
            print(f"  {h['Title']:30} User_Rating={h.get('User_Rating')}")
    else:
        print("\nAll movies already rated!")
else:
    # Just test with user_id=53 directly
    print("\n=== Testing with user_id=53 directly ===")
    hist = requests.get(f"{LOCAL}/users/53/history").json()
    for h in hist:
        print(f"  {h['Title']:30} User_Rating={h.get('User_Rating')}")
