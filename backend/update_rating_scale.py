"""
Update the ratings table to accept 0-10 scale directly
"""
import psycopg2

DATABASE_URL = "postgresql://postgres:doBjXlXqMXEtvQxvVAQqqqWioUfpCHmh@caboose.proxy.rlwy.net:33590/railway"

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

print("=== UPDATING RATING SCALE TO 0-10 ===")

# 1. Drop the check constraint
print("1. Dropping ratings_score_check constraint...")
cursor.execute("""
    ALTER TABLE ratings 
    DROP CONSTRAINT IF EXISTS ratings_score_check
""")
print("   ✅ Constraint dropped")

# 2. Add new check constraint for 0-10
print("2. Adding new constraint for 0-10 scale...")
cursor.execute("""
    ALTER TABLE ratings 
    ADD CONSTRAINT ratings_score_check CHECK (score >= 0 AND score <= 10)
""")
print("   ✅ New constraint added (0-10)")

# 3. Update existing ratings from 1-5 to 1-10 scale (multiply by 2)
print("3. Converting existing ratings to 0-10 scale...")
cursor.execute("""
    UPDATE ratings 
    SET score = score * 2 
    WHERE score <= 5
""")
updated = cursor.rowcount
print(f"   ✅ Updated {updated} existing ratings to 0-10 scale")

# 4. Verify the changes
print("4. Verifying changes...")
cursor.execute("SELECT MIN(score) as min_score, MAX(score) as max_score, COUNT(*) as count FROM ratings")
result = cursor.fetchone()
print(f"   Rating range: {result[0]} to {result[1]}, Total: {result[2]}")

# 5. Show sample ratings
print("5. Sample ratings:")
cursor.execute("SELECT user_id, movie_id, score FROM ratings ORDER BY rating_id DESC LIMIT 5")
for r in cursor.fetchall():
    print(f"   User {r[0]}, Movie {r[1]}, Score {r[2]}")

conn.commit()
conn.close()

print("\n=== DATABASE UPDATED TO 0-10 SCALE ===")
print("Now update frontend to send 0-10 directly without conversion")
