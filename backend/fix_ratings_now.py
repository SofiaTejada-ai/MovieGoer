import requests
import psycopg2
import psycopg2.extras

BACKEND_URL = "https://moviegoer-production.up.railway.app"
DATABASE_URL = "postgresql://postgres:REDACTED@caboose.proxy.rlwy.net:33590/railway"

USER_ID = 53

# First clean up duplicates
conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)
cursor = conn.cursor()

cursor.execute("""
    DELETE FROM watch_history
    WHERE ctid NOT IN (
        SELECT DISTINCT ON (movie_id) ctid
        FROM watch_history
        WHERE user_id = %s
        ORDER BY movie_id, watched_date DESC
    )
    AND user_id = %s
""", (USER_ID, USER_ID))
print(f"Cleaned {cursor.rowcount} duplicate watch_history entries")
conn.commit()

# Delete the wrong test rating (Whiplash movie_id=10 isn't in her history)
cursor.execute("DELETE FROM ratings WHERE user_id = %s AND movie_id = 10", (USER_ID,))
print(f"Removed test Whiplash rating")
conn.commit()

# Get her actual watch history movies
cursor.execute("""
    SELECT wh.movie_id, m.title
    FROM watch_history wh
    JOIN movies m ON wh.movie_id = m.movie_id
    WHERE wh.user_id = %s
""", (USER_ID,))
movies = cursor.fetchall()
print(f"\nHer watched movies:")
for m in movies:
    print(f"  movie_id={m['movie_id']} {m['title']}")

# Now POST ratings via the API for each movie (score=5 as placeholder)
print("\nPosting ratings via API...")
for m in movies:
    mid = m['movie_id']
    title = m['title']
    # Check if rating already exists
    cursor.execute("SELECT score FROM ratings WHERE user_id = %s AND movie_id = %s", (USER_ID, mid))
    existing = cursor.fetchone()
    if existing:
        print(f"  {title}: already rated {existing['score']}, skipping")
        continue
    
    payload = {"User_id": USER_ID, "Movie_id": mid, "Score": 5}
    resp = requests.post(f"{BACKEND_URL}/ratings", json=payload, timeout=10)
    print(f"  {title} (id={mid}): {resp.status_code} - {resp.json()}")

# Verify final state
print("\n=== FINAL STATE ===")
cursor.execute("""
    SELECT wh.movie_id, m.title, r.score as user_rating
    FROM watch_history wh
    JOIN movies m ON wh.movie_id = m.movie_id
    LEFT JOIN ratings r ON wh.movie_id = r.movie_id AND wh.user_id = r.user_id
    WHERE wh.user_id = %s
    ORDER BY wh.watched_date DESC
""", (USER_ID,))
for r in cursor.fetchall():
    print(f"  {r['title']:30} rating={r['user_rating']}")

# Now test the history API endpoint
print("\n=== HISTORY API RESPONSE ===")
resp = requests.get(f"{BACKEND_URL}/users/{USER_ID}/history", timeout=10)
for item in resp.json():
    print(f"  {item['Title']:30} User_Rating={item.get('User_Rating')}")

conn.close()
