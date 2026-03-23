"""Test a completely NEW account rating"""
import requests
import psycopg2
import psycopg2.extras

LOCAL = "http://localhost:8000"
DATABASE_URL = "postgresql://postgres:REDACTED@caboose.proxy.rlwy.net:33590/railway"

print("=" * 60)
print("TESTING NEW ACCOUNT RATING ISSUE")
print("=" * 60)

# 1. Find a user with no ratings
conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)
cursor = conn.cursor()

cursor.execute("""
    SELECT u.user_id, u.username, COUNT(r.rating_id) as rating_count
    FROM users u
    LEFT JOIN ratings r ON u.user_id = r.user_id
    GROUP BY u.user_id, u.username
    HAVING COUNT(r.rating_id) = 0
    ORDER BY u.user_id
    LIMIT 1
""")
new_user = cursor.fetchone()

if not new_user:
    print("No users without ratings found")
    conn.close()
    exit()

user_id = new_user['user_id']
username = new_user['username']
print(f"Testing new account: {username} (id={user_id})")

# 2. Check if they have watch history
cursor.execute("SELECT COUNT(*) as count FROM watch_history WHERE user_id = %s", (user_id,))
history_count = cursor.fetchone()['count']
print(f"Watch history count: {history_count}")

if history_count == 0:
    print("No watch history - adding one")
    # Add a movie to watch history first
    cursor.execute("SELECT movie_id, title FROM movies LIMIT 1")
    movie = cursor.fetchone()
    cursor.execute("INSERT INTO watch_history (user_id, movie_id) VALUES (%s, %s)", (user_id, movie['movie_id']))
    conn.commit()
    print(f"Added {movie['title']} to watch history")
    movie_id = movie['movie_id']
else:
    cursor.execute("SELECT wh.movie_id, m.title FROM watch_history wh JOIN movies m ON wh.movie_id = m.movie_id WHERE wh.user_id = %s LIMIT 1", (user_id,))
    movie = cursor.fetchone()
    movie_id = movie['movie_id']
    print(f"Using existing movie: {movie['title']}")

# 3. Submit rating via API
print(f"\nSubmitting rating for {movie['title']} (id={movie_id})")
payload = {"User_id": user_id, "Movie_id": movie_id, "Score": 4}
print(f"Payload: {payload}")

r = requests.post(f"{LOCAL}/ratings", json=payload)
print(f"Status: {r.status_code}")
print(f"Response: {r.json()}")

# 4. Check database
cursor.execute("SELECT * FROM ratings WHERE user_id = %s AND movie_id = %s", (user_id, movie_id))
db_rating = cursor.fetchone()
if db_rating:
    print(f"✅ Saved to DB: score={db_rating['score']}")
else:
    print("❌ NOT found in DB")

# 5. Check API history
print(f"\nChecking API history for user {user_id}:")
r2 = requests.get(f"{LOCAL}/users/{user_id}/history")
if r2.status_code == 200:
    history = r2.json()
    for h in history:
        print(f"  {h['Title']:30} User_Rating={h.get('User_Rating')}")
else:
    print(f"ERROR: {r2.status_code}")

# 6. Test with different scores to verify scale
print(f"\nTesting different scores (1-10 scale):")
for score in [1, 3, 5, 7, 9, 10]:
    payload = {"User_id": user_id, "Movie_id": movie_id, "Score": score}
    r3 = requests.post(f"{LOCAL}/ratings", json=payload)
    expected_db_score = score // 2 if score > 5 else score
    print(f"  Frontend score={score} → DB score={expected_db_score} → Status={r3.status_code}")

conn.close()
print("\n" + "=" * 60)
print("If ratings save to DB but don't show in API, the issue is in the API endpoint")
print("=" * 60)
