import psycopg2
import psycopg2.extras
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:doBjXlXqMXEtvQxvVAQqqqWioUfpCHmh@caboose.proxy.rlwy.net:33590/railway")

conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)
cursor = conn.cursor()

cursor.execute("SELECT movie_id, title, release_year FROM movies WHERE title ILIKE %s", ("%conjuring%",))
results = cursor.fetchall()

if results:
    for row in results:
        print(f"Found: {row['title']} (ID: {row['movie_id']}, Year: {row['release_year']})")
else:
    print("No Conjuring movies found")

conn.close()
