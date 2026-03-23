import psycopg2
import psycopg2.extras

DATABASE_URL = "postgresql://postgres:doBjXlXqMXEtvQxvVAQqqqWioUfpCHmh@caboose.proxy.rlwy.net:33590/railway"

conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)
cursor = conn.cursor()

# Check ALL ratings for user 53
cursor.execute("SELECT r.movie_id, m.title, r.score FROM ratings r JOIN movies m ON r.movie_id = m.movie_id WHERE r.user_id = 53")
ratings = cursor.fetchall()
print(f"=== CarolinaSarria ratings in DB: {len(ratings)} ===")
for r in ratings:
    print(f"  movie_id={r['movie_id']} {r['title']} score={r['score']}")

# Check what the history endpoint actually returns
cursor.execute("""
    SELECT wh.movie_id, m.title, m.poster_url, wh.watched_date, r.score as user_rating
    FROM watch_history wh
    JOIN movies m ON wh.movie_id = m.movie_id
    LEFT JOIN ratings r ON wh.movie_id = r.movie_id AND wh.user_id = r.user_id
    WHERE wh.user_id = 53
    ORDER BY wh.watched_date DESC
""")
print(f"\n=== History endpoint would return: ===")
for r in cursor.fetchall():
    print(f"  {r['title']:30} User_Rating={r['user_rating']}")

# Check if deployment is using the right code - look at recent rating attempts
cursor.execute("SELECT * FROM ratings ORDER BY rating_id DESC LIMIT 5")
print(f"\n=== Last 5 ratings in DB (any user): ===")
for r in cursor.fetchall():
    print(f"  {dict(r)}")

conn.close()
