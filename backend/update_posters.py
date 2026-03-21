import psycopg2

DATABASE_URL = "postgresql://postgres:doBjXlXqMXEtvQxvVAQqqqWioUfpCHmh@caboose.proxy.rlwy.net:33590/railway"

updates = [
    ("The Grand Budapest Hotel", "https://peterviney.files.wordpress.com/2014/03/grand-budapest-hotel.png"),
]

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cursor = conn.cursor()

for title, url in updates:
    cursor.execute("UPDATE movies SET poster_url = %s WHERE title = %s", (url, title))
    print(f"✓ Updated {title}")

cursor.close()
conn.close()
print("\n✅ All poster URLs updated!")
