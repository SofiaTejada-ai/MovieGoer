import psycopg2

DATABASE_URL = "postgresql://postgres:REDACTED@caboose.proxy.rlwy.net:33590/railway"

print("Connecting to Railway PostgreSQL...")
conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cursor = conn.cursor()

print("Running migration script...")

with open("init_postgres.sql", "r", encoding="utf-8") as f:
    sql = f.read()

# Execute the entire script at once
try:
    cursor.execute(sql)
    print("✅ All statements executed successfully!")
except Exception as e:
    print(f"Error: {e}")
    print("\nTrying to drop and recreate tables...")
    
    # Drop all tables first
    drop_sql = """
    DROP TABLE IF EXISTS movie_streaming CASCADE;
    DROP TABLE IF EXISTS streaming_services CASCADE;
    DROP TABLE IF EXISTS user_preferences CASCADE;
    DROP TABLE IF EXISTS watch_history CASCADE;
    DROP TABLE IF EXISTS ratings CASCADE;
    DROP TABLE IF EXISTS movie_genres CASCADE;
    DROP TABLE IF EXISTS genres CASCADE;
    DROP TABLE IF EXISTS movies CASCADE;
    DROP TABLE IF EXISTS users CASCADE;
    """
    cursor.execute(drop_sql)
    print("Tables dropped.")
    
    # Re-run the migration
    cursor.execute(sql)
    print("✅ Migration successful after reset!")

cursor.close()
conn.close()
print("\n✅ Database ready!")
