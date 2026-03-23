import psycopg2
import psycopg2.extras

DATABASE_URL = "postgresql://postgres:REDACTED@caboose.proxy.rlwy.net:33590/railway"

conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)
cursor = conn.cursor()

# Check if ratings table has foreign key constraints
cursor.execute("""
    SELECT tc.constraint_name, kcu.column_name, ccu.table_name AS foreign_table
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
    WHERE tc.table_name = 'ratings' AND tc.constraint_type = 'FOREIGN KEY'
""")
print("=== RATINGS TABLE FK CONSTRAINTS ===")
for r in cursor.fetchall():
    print(f"  {r['constraint_name']}: {r['column_name']} -> {r['foreign_table']}")

# Check if there are any ratings for user_id=1 (the default fallback)
cursor.execute("SELECT * FROM ratings WHERE user_id = 1")
rows = cursor.fetchall()
print(f"\n=== Ratings for user_id=1 (default fallback): {len(rows)} ===")
for r in rows:
    print(f"  {dict(r)}")

# Check all ratings
cursor.execute("SELECT r.user_id, u.username, r.movie_id, m.title, r.score FROM ratings r LEFT JOIN users u ON r.user_id = u.user_id LEFT JOIN movies m ON r.movie_id = m.movie_id ORDER BY r.user_id")
print(f"\n=== ALL RATINGS ===")
for r in cursor.fetchall():
    print(f"  User {r['user_id']} ({r['username']}): {r['title']} = {r['score']}")

# Check CarolinaSarria specifically
cursor.execute("SELECT user_id FROM users WHERE username = 'CarolinaSarria'")
carolina = cursor.fetchone()
if carolina:
    uid = carolina['user_id']
    print(f"\n=== CarolinaSarria (user_id={uid}) ===")
    cursor.execute("SELECT * FROM watch_history WHERE user_id = %s", (uid,))
    print(f"  Watch history: {len(cursor.fetchall())} entries")
    cursor.execute("SELECT * FROM ratings WHERE user_id = %s", (uid,))
    print(f"  Ratings: {len(cursor.fetchall())} entries")

# Try inserting a test rating for CarolinaSarria to see if it works
    cursor.execute("SELECT wh.movie_id FROM watch_history wh WHERE wh.user_id = %s LIMIT 1", (uid,))
    movie = cursor.fetchone()
    if movie:
        mid = movie['movie_id']
        try:
            cursor.execute("INSERT INTO ratings (user_id, movie_id, score) VALUES (%s, %s, %s)", (uid, mid, 4))
            conn.commit()
            print(f"  TEST: Successfully inserted rating for movie_id={mid}")
        except Exception as e:
            conn.rollback()
            print(f"  TEST: Failed to insert rating: {e}")

conn.close()
