import psycopg2
import psycopg2.extras

DATABASE_URL = "postgresql://postgres:doBjXlXqMXEtvQxvVAQqqqWioUfpCHmh@caboose.proxy.rlwy.net:33590/railway"

conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)
cursor = conn.cursor()

user_id = 53

# Remove duplicate watch_history entries, keep only the latest per movie
cursor.execute("""
    DELETE FROM watch_history
    WHERE ctid NOT IN (
        SELECT DISTINCT ON (movie_id) ctid
        FROM watch_history
        WHERE user_id = %s
        ORDER BY movie_id, watched_date DESC
    )
    AND user_id = %s
""", (user_id, user_id))
deleted = cursor.rowcount
print(f"Removed {deleted} duplicate watch_history entries for CarolinaSarria")

conn.commit()

# Show clean state
cursor.execute("""
    SELECT wh.movie_id, m.title, wh.watched_date, r.score
    FROM watch_history wh
    JOIN movies m ON wh.movie_id = m.movie_id
    LEFT JOIN ratings r ON wh.movie_id = r.movie_id AND wh.user_id = r.user_id
    WHERE wh.user_id = %s
    ORDER BY wh.watched_date DESC
""", (user_id,))
print("\nClean history:")
for row in cursor.fetchall():
    rating = row['score'] if row['score'] else "NEEDS RE-RATING"
    print(f"  {row['title']:30} {rating}")

conn.close()
