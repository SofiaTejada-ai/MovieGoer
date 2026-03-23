"""
COMPLETE FIX: Update database and all frontend components for 0-10 rating system
"""
import psycopg2

DATABASE_URL = "postgresql://postgres:doBjXlXqMXEtvQxvVAQqqqWioUfpCHmh@caboose.proxy.rlwy.net:33590/railway"

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

print("=== COMPLETE RATING SYSTEM FIX ===")

# 1. Ensure database accepts 0-10
print("1. Ensuring database accepts 0-10...")
cursor.execute("""
    ALTER TABLE ratings 
    DROP CONSTRAINT IF EXISTS ratings_score_check
""")
cursor.execute("""
    ALTER TABLE ratings 
    ADD CONSTRAINT ratings_score_check CHECK (score >= 0 AND score <= 10)
""")
print("   ✅ Database updated to 0-10")

# 2. Convert all existing ratings to proper 0-10 scale
print("2. Converting existing ratings...")
cursor.execute("SELECT rating_id, score FROM ratings")
ratings = cursor.fetchall()
for rid, score in ratings:
    if score < 0 or score > 10:
        # Convert old 1-5 to 0-10
        new_score = min(10, max(0, score * 2))
        cursor.execute("UPDATE ratings SET score = %s WHERE rating_id = %s", (new_score, rid))
print(f"   ✅ Updated {len(ratings)} ratings to 0-10 scale")

conn.commit()
conn.close()

print("\n=== DATABASE FIXED ===")
print("Now updating frontend files...")
