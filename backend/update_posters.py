import psycopg2

DATABASE_URL = "postgresql://postgres:doBjXlXqMXEtvQxvVAQqqqWioUfpCHmh@caboose.proxy.rlwy.net:33590/railway"

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cursor = conn.cursor()

# Update Get Out poster
cursor.execute("UPDATE movies SET poster_url = %s WHERE title = %s", 
    ("https://media.themoviedb.org/t/p/w440_and_h660_face/xxVEd77IKrPRlm7xNY46bDnPZ8Z.jpg", "Get Out"))
print(f"✓ Updated Get Out: {cursor.rowcount} rows")

# If not found, try ILIKE
if cursor.rowcount == 0:
    cursor.execute("UPDATE movies SET poster_url = %s WHERE title ILIKE %s", 
        ("https://media.themoviedb.org/t/p/w440_and_h660_face/xxVEd77IKrPRlm7xNY46bDnPZ8Z.jpg", "%get out%"))
    print(f"✓ Updated with ILIKE: {cursor.rowcount} rows")

cursor.close()
conn.close()
print("\n✅ All poster URLs updated!")
