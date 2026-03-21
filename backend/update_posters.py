import psycopg2

DATABASE_URL = "postgresql://postgres:doBjXlXqMXEtvQxvVAQqqqWioUfpCHmh@caboose.proxy.rlwy.net:33590/railway"

updates = [
    ("Avengers: Endgame", "https://lumiere-a.akamaihd.net/v1/images/p_avengersendgame_19751_e14a0104.jpeg"),
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
