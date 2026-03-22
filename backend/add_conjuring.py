import psycopg2
import psycopg2.extras
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:doBjXlXqMXEtvQxvVAQqqqWioUfpCHmh@caboose.proxy.rlwy.net:33590/railway")

conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)
cursor = conn.cursor()

# Conjuring movies to add
movies = [
    {
        "title": "The Conjuring",
        "poster_url": "https://m.media-amazon.com/images/S/pv-target-images/8c40e2e1933163be44c6652a7d8a1bb67822385d84e4caf3750da580c981e2db.jpg",
        "genres": ["Horror", "Mystery", "Thriller"],
        "release_year": 2013,
        "runtime": 112,
        "language": "English",
        "country": "USA",
        "overview": "Paranormal investigators Ed and Lorraine Warren work to help a family terrorized by a dark presence in their farmhouse.",
        "media_franchise": "The Conjuring Universe",
        "sequel_franchise": "The Conjuring Series",
        "streaming": ["HBO Max", "Amazon Video", "Apple TV Store", "Fandango At Home"]
    },
    {
        "title": "The Conjuring 2",
        "poster_url": "https://tse4.mm.bing.net/th/id/OIP.Pbp0fq_T-AD1RboFAb6WGgHaLH?rs=1&pid=ImgDetMain&o=7&rm=3",
        "genres": ["Horror", "Mystery", "Thriller"],
        "release_year": 2016,
        "runtime": 134,
        "language": "English",
        "country": "USA",
        "overview": "Ed and Lorraine Warren travel to North London to help a single mother raising four children alone in a house plagued by malicious spirits.",
        "media_franchise": "The Conjuring Universe",
        "sequel_franchise": "The Conjuring Series",
        "streaming": ["HBO Max", "Amazon Video", "Apple TV Store", "Fandango At Home"]
    },
    {
        "title": "Annabelle",
        "poster_url": "https://image.tmdb.org/t/p/original/sCPwduyyqCrIpSk1kA0p8lwjveB.jpg",
        "genres": ["Horror", "Mystery", "Thriller"],
        "release_year": 2014,
        "runtime": 99,
        "language": "English",
        "country": "USA",
        "overview": "A couple begins to experience terrifying supernatural occurrences involving a vintage doll shortly after their home is invaded by satanic cultists.",
        "media_franchise": "The Conjuring Universe",
        "sequel_franchise": "Annabelle Series",
        "streaming": ["HBO Max", "Amazon Video", "Apple TV Store", "Fandango At Home"]
    }
]

# Get existing genres
cursor.execute("SELECT genre_id, genre_name FROM genres")
genres_map = {row["genre_name"].lower(): row["genre_id"] for row in cursor.fetchall()}
print(f"Available genres: {list(genres_map.keys())}")

# Get existing streaming services
cursor.execute("SELECT streaming_service_id, service_name FROM streaming_services")
streaming_map = {row["service_name"].lower(): row["streaming_service_id"] for row in cursor.fetchall()}
print(f"Available streaming services: {list(streaming_map.keys())}")

for movie in movies:
    # Check if movie already exists
    cursor.execute("SELECT movie_id FROM movies WHERE title = %s", (movie["title"],))
    existing = cursor.fetchone()
    
    if existing:
        print(f"⚠️ Movie '{movie['title']}' already exists, skipping...")
        continue
    
    # Insert movie
    cursor.execute("""
        INSERT INTO movies (title, poster_url, release_year, runtime, language, country, overview, average_rating, popularity_score)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING movie_id
    """, (
        movie["title"],
        movie["poster_url"],
        movie["release_year"],
        movie["runtime"],
        movie["language"],
        movie["country"],
        movie["overview"],
        7.5,  # default rating
        50.0  # default popularity
    ))
    movie_id = cursor.fetchone()["movie_id"]
    print(f"✅ Added movie: {movie['title']} (ID: {movie_id})")
    
    # Link genres
    for genre in movie["genres"]:
        genre_lower = genre.lower()
        if genre_lower in genres_map:
            cursor.execute("""
                INSERT INTO movie_genres (movie_id, genre_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (movie_id, genres_map[genre_lower]))
            print(f"   ↳ Linked genre: {genre}")
        else:
            print(f"   ⚠️ Genre '{genre}' not found in database")
    
    # Link franchise
    if movie.get("media_franchise") or movie.get("sequel_franchise"):
        cursor.execute("SELECT movie_id FROM franchises WHERE movie_id = %s", (movie_id,))
        if cursor.fetchone():
            cursor.execute("""
                UPDATE franchises SET media_franchise = %s, sequel_franchise = %s WHERE movie_id = %s
            """, (movie.get("media_franchise"), movie.get("sequel_franchise"), movie_id))
        else:
            cursor.execute("""
                INSERT INTO franchises (movie_id, media_franchise, sequel_franchise)
                VALUES (%s, %s, %s)
            """, (movie_id, movie.get("media_franchise"), movie.get("sequel_franchise")))
        print(f"   ↳ Linked franchise: {movie.get('media_franchise')} -> {movie.get('sequel_franchise')}")
    
    # Link streaming services
    for service in movie.get("streaming", []):
        service_lower = service.lower()
        if service_lower in streaming_map:
            # Generate a placeholder streaming URL
            streaming_url = f"https://{service_lower.replace(' ', '')}.com/watch/{movie['title'].lower().replace(' ', '-')}"
            cursor.execute("""
                INSERT INTO movie_streaming (movie_id, streaming_service_id, streaming_url)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (movie_id, streaming_map[service_lower], streaming_url))
            print(f"   ↳ Linked streaming: {service}")
        else:
            print(f"   ⚠️ Streaming service '{service}' not found")

conn.commit()
conn.close()
print("\n✅ All Conjuring movies added! Backend will reload model on next deploy.")
