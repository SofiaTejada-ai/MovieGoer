"""Test MoonPie rating issue in detail"""
import requests
import psycopg2
import psycopg2.extras

LOCAL = "http://localhost:8000"
DATABASE_URL = "postgresql://postgres:REDACTED@caboose.proxy.rlwy.net:33590/railway"

MOONPIE_ID = 46

print("=" * 60)
print("TESTING MOONPIE (user_id=46) RATING ISSUE")
print("=" * 60)

conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)
cursor = conn.cursor()

# 1. Check MoonPie's current ratings in DB
print("\n1. MoonPie's ratings in database:")
cursor.execute("""
    SELECT r.movie_id, m.title, r.score, r.rated_at
    FROM ratings r
    JOIN movies m ON r.movie_id = m.movie_id
    WHERE r.user_id = %s
    ORDER BY r.rated_at DESC
""", (MOONPIE_ID,))
db_ratings = cursor.fetchall()
for r in db_ratings:
    print(f"  movie_id={r['movie_id']} {r['title']} score={r['score']} at {r['rated_at']}")

# 2. Check MoonPie's history via API
print("\n2. MoonPie's history via API:")
try:
    r = requests.get(f"{LOCAL}/users/{MOONPIE_ID}/history")
    api_history = r.json()
    for h in api_history:
        print(f"  {h['Title']:30} User_Rating={h.get('User_Rating')}")
except Exception as e:
    print(f"  ERROR: {e}")

# 3. Find an unrated movie for MoonPie to test
print("\n3. Finding unrated movie for test:")
cursor.execute("""
    SELECT wh.movie_id, m.title
    FROM watch_history wh
    JOIN movies m ON wh.movie_id = m.movie_id
    LEFT JOIN ratings r ON wh.movie_id = r.movie_id AND wh.user_id = r.user_id
    WHERE wh.user_id = %s AND r.score IS NULL
    LIMIT 1
""", (MOONPIE_ID,))
unrated = cursor.fetchone()
if unrated:
    print(f"  Found: {unrated['title']} (id={unrated['movie_id']})")
    
    # 4. Submit test rating
    print("\n4. Submitting test rating:")
    payload = {"User_id": MOONPIE_ID, "Movie_id": unrated['movie_id'], "Score": 4}
    print(f"  Payload: {payload}")
    
    r2 = requests.post(f"{LOCAL}/ratings", json=payload)
    print(f"  Status: {r2.status_code}")
    print(f"  Response: {r2.json()}")
    
    # 5. Check if it saved to DB
    print("\n5. Verify saved to DB:")
    cursor.execute("""
        SELECT r.movie_id, m.title, r.score, r.rated_at
        FROM ratings r
        JOIN movies m ON r.movie_id = m.movie_id
        WHERE r.user_id = %s AND r.movie_id = %s
    """, (MOONPIE_ID, unrated['movie_id']))
    saved = cursor.fetchone()
    if saved:
        print(f"  ✅ Saved: {saved['title']} score={saved['score']}")
    else:
        print(f"  ❌ NOT FOUND in DB")
    
    # 6. Check API again
    print("\n6. Check API again:")
    r3 = requests.get(f"{LOCAL}/users/{MOONPIE_ID}/history")
    updated_history = r3.json()
    for h in updated_history:
        if h['Movie_id'] == unrated['movie_id']:
            print(f"  {h['Title']:30} User_Rating={h.get('User_Rating')}")
            break
else:
    print("  No unrated movies found")

conn.close()
print("\n" + "=" * 60)
print("DONE")
print("=" * 60)
