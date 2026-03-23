"""Test ratings for ALL user accounts"""
import requests
import psycopg2
import psycopg2.extras

LOCAL = "http://localhost:8000"
DATABASE_URL = "postgresql://postgres:REDACTED@caboose.proxy.rlwy.net:33590/railway"

print("=" * 60)
print("CHECKING ALL USERS AND THEIR RATINGS")
print("=" * 60)

# Get all users
conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)
cursor = conn.cursor()
cursor.execute("SELECT user_id, username FROM users ORDER BY user_id")
users = cursor.fetchall()

for user in users:
    uid = user['user_id']
    username = user['username']
    
    print(f"\n--- User {uid}: {username} ---")
    
    # Check history via API
    try:
        r = requests.get(f"{LOCAL}/users/{uid}/history", timeout=5)
        if r.status_code == 200:
            history = r.json()
            rated_count = sum(1 for h in history if h.get('User_Rating') is not None)
            print(f"  History: {len(history)} movies, {rated_count} with ratings")
            
            # Show rated movies
            for h in history:
                if h.get('User_Rating') is not None:
                    print(f"    {h['Title']:30} rating={h['User_Rating']}")
        else:
            print(f"  ERROR: {r.status_code}")
    except Exception as e:
        print(f"  ERROR: {e}")

print("\n" + "=" * 60)
print("TESTING NEW RATING FOR TESTUSER5 (user_id=45)")
print("=" * 60)

# Test rating for TestUser5
test_user = 45
try:
    # Get their history
    r = requests.get(f"{LOCAL}/users/{test_user}/history")
    history = r.json()
    
    # Find an unrated movie
    unrated = [h for h in history if h.get('User_Rating') is None]
    if unrated:
        movie = unrated[0]
        print(f"Rating {movie['Title']} (id={movie['Movie_id']})")
        
        # Submit rating
        payload = {"User_id": test_user, "Movie_id": movie['Movie_id'], "Score": 4}
        r2 = requests.post(f"{LOCAL}/ratings", json=payload)
        print(f"Status: {r2.status_code} Response: {r2.json()}")
        
        # Verify
        r3 = requests.get(f"{LOCAL}/users/{test_user}/history")
        updated = [h for h in r3.json() if h['Movie_id'] == movie['Movie_id']][0]
        print(f"New rating: {updated.get('User_Rating')}")
    else:
        print("All movies already rated")
except Exception as e:
    print(f"ERROR: {e}")

conn.close()
print("\n" + "=" * 60)
print("DONE")
print("=" * 60)
