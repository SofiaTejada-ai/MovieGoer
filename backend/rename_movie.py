import psycopg2
import psycopg2.extras

DATABASE_URL = "postgresql://postgres:REDACTED@caboose.proxy.rlwy.net:33590/railway"

conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)
cursor = conn.cursor()

cursor.execute("""
    UPDATE movies 
    SET overview = 'A documentary chronicling the rise of the San Francisco Bay Area thrash metal scene, featuring interviews and archival footage of bands like Metallica, Megadeth, Slayer, Exodus, and Testament that defined a generation of heavy metal music.'
    WHERE movie_id = 125
    RETURNING movie_id, title, overview
""")

result = cursor.fetchone()
if result:
    print(f"✅ Updated: ID {result['movie_id']} -> {result['title']}")
    conn.commit()
else:
    print("❌ Movie not found")

conn.close()
