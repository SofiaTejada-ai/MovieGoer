import psycopg2
import psycopg2.extras

DATABASE_URL = "postgresql://postgres:REDACTED@caboose.proxy.rlwy.net:33590/railway"

conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)
cursor = conn.cursor()

# Check all users and their history/ratings counts
cursor.execute("""
    SELECT u.user_id, u.username, 
           (SELECT COUNT(*) FROM watch_history wh WHERE wh.user_id = u.user_id) as history_count,
           (SELECT COUNT(*) FROM ratings r WHERE r.user_id = u.user_id) as rating_count
    FROM users u
    ORDER BY u.user_id
""")
rows = cursor.fetchall()

print("user_id | username | history | ratings")
print("-" * 50)
for r in rows:
    print(f"{r['user_id']:7} | {r['username'][:15]:15} | {r['history_count']:7} | {r['rating_count']}")

# Check specific history with ratings for users who have history
print("\n\nDetailed history with ratings:")
print("-" * 70)
cursor.execute("""
    SELECT wh.user_id, u.username, m.title, wh.watched_date, r.score
    FROM watch_history wh
    JOIN users u ON wh.user_id = u.user_id
    JOIN movies m ON wh.movie_id = m.movie_id
    LEFT JOIN ratings r ON wh.movie_id = r.movie_id AND wh.user_id = r.user_id
    ORDER BY wh.user_id, wh.watched_date DESC
    LIMIT 20
""")
rows = cursor.fetchall()
for r in rows:
    rating = r['score'] if r['score'] else "NO RATING"
    print(f"User {r['user_id']} ({r['username'][:10]}): {r['title'][:30]} - {rating}")

conn.close()
