"""
Test the FULL rating flow end-to-end:
1. Submit a rating via the API (same way frontend does)
2. Verify it saved in DB
3. Verify history endpoint returns it
"""
import requests
import psycopg2
import psycopg2.extras

# Config - use the deployed Railway backend
BACKEND_URL = "https://moviegoer-production.up.railway.app"
DATABASE_URL = "postgresql://postgres:REDACTED@caboose.proxy.rlwy.net:33590/railway"

USER_ID = 53  # CarolinaSarria
TEST_MOVIE_ID = 10  # Braveheart

print("=" * 60)
print("TEST 1: Direct DB check - what ratings does user 53 have?")
print("=" * 60)
conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)
cursor = conn.cursor()
cursor.execute("SELECT r.movie_id, m.title, r.score FROM ratings r JOIN movies m ON r.movie_id = m.movie_id WHERE r.user_id = %s", (USER_ID,))
rows = cursor.fetchall()
print(f"  Ratings count: {len(rows)}")
for r in rows:
    print(f"  movie_id={r['movie_id']} {r['title']} score={r['score']}")

print("\n" + "=" * 60)
print("TEST 2: POST rating via API (like frontend does)")
print("=" * 60)
payload = {"User_id": USER_ID, "Movie_id": TEST_MOVIE_ID, "Score": 5}
print(f"  Sending: {payload}")
try:
    resp = requests.post(f"{BACKEND_URL}/ratings", json=payload, timeout=10)
    print(f"  Status: {resp.status_code}")
    print(f"  Response: {resp.json()}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n" + "=" * 60)
print("TEST 3: Verify rating saved in DB")
print("=" * 60)
cursor.execute("SELECT r.movie_id, m.title, r.score FROM ratings r JOIN movies m ON r.movie_id = m.movie_id WHERE r.user_id = %s", (USER_ID,))
rows = cursor.fetchall()
print(f"  Ratings count: {len(rows)}")
for r in rows:
    print(f"  movie_id={r['movie_id']} {r['title']} score={r['score']}")

print("\n" + "=" * 60)
print("TEST 4: GET history via API (like frontend does)")
print("=" * 60)
try:
    resp = requests.get(f"{BACKEND_URL}/users/{USER_ID}/history", timeout=10)
    print(f"  Status: {resp.status_code}")
    history = resp.json()
    for item in history:
        print(f"  {item['Title']:30} User_Rating={item.get('User_Rating')}")
except Exception as e:
    print(f"  ERROR: {e}")

# Find Braveheart movie_id
cursor.execute("SELECT movie_id FROM movies WHERE title ILIKE '%braveheart%'")
bh = cursor.fetchone()
if bh:
    print(f"\n  NOTE: Braveheart movie_id = {bh['movie_id']}")

# Find WALL-E and Casablanca movie_ids
cursor.execute("SELECT movie_id, title FROM movies WHERE title ILIKE '%wall%' OR title ILIKE '%casablanca%'")
for r in cursor.fetchall():
    print(f"  NOTE: {r['title']} movie_id = {r['movie_id']}")

conn.close()
print("\n" + "=" * 60)
print("DONE")
print("=" * 60)
