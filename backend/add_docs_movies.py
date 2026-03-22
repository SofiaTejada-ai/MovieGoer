import psycopg2
import psycopg2.extras
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:doBjXlXqMXEtvQxvVAQqqqWioUfpCHmh@caboose.proxy.rlwy.net:33590/railway")

conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)
cursor = conn.cursor()

# Movies to add
movies = [
    {
        "title": "Cave of Forgotten Dreams",
        "poster_url": "https://image.tmdb.org/t/p/original/qjr4q9JLXcoLbtwowfhKASGTZrY.jpg",
        "genres": ["Documentary", "History"],
        "release_year": 2010,
        "runtime": 90,
        "language": "English",
        "country": "USA",
        "overview": "Werner Herzog gains exclusive access to film inside the Chauvet caves of Southern France, capturing the oldest known pictorial creations of humankind.",
        "streaming": []
    },
    {
        "title": "Pompeii: Disaster Street",
        "poster_url": "https://img.rgstatic.com/content/movie/e7a38a8b-b0f6-4d69-885d-79faf896c3ac/poster-342.jpg",
        "genres": ["Documentary", "History"],
        "release_year": 2020,
        "runtime": 60,
        "language": "English",
        "country": "UK",
        "overview": "A documentary exploring the ancient Roman city of Pompeii and the catastrophic eruption of Mount Vesuvius.",
        "streaming": []
    },
    {
        "title": "A Quiet Place",
        "poster_url": "https://wwwimage-us.pplusstatic.com/thumbnails/photos/370-q80/movie_asset/92/47/97/AQP1_SAlone_Poster_1400x2100.jpg",
        "genres": ["Horror", "Thriller", "Sci-Fi"],
        "release_year": 2018,
        "runtime": 90,
        "language": "English",
        "country": "USA",
        "overview": "In a post-apocalyptic world, a family must live in silence while hiding from monsters with ultra-sensitive hearing.",
        "streaming": ["Paramount+", "Amazon Video", "Apple TV Store", "Fandango At Home"]
    },
    {
        "title": "Hype!",
        "poster_url": "https://rockintersection.com/wp-content/uploads/2024/01/image-1.png",
        "genres": ["Documentary", "Music"],
        "release_year": 1996,
        "runtime": 84,
        "language": "English",
        "country": "USA",
        "overview": "A documentary about the Seattle grunge music scene and the bands that emerged from it, including Nirvana, Pearl Jam, and Soundgarden.",
        "streaming": ["Amazon Prime Video", "Pluto TV", "Fandango At Home"]
    },
    {
        "title": "Rush: Beyond the Lighted Stage",
        "poster_url": "https://m.media-amazon.com/images/S/pv-target-images/bee0739d14e94e21417c13ed9b3d3958537cf8a984bff129a0e747efe8f9ddd7.jpg",
        "genres": ["Documentary", "Music"],
        "release_year": 2010,
        "runtime": 107,
        "language": "English",
        "country": "Canada",
        "overview": "A documentary following the Canadian rock band Rush, chronicling their rise to fame and enduring legacy.",
        "streaming": ["Amazon Prime Video"]
    },
    {
        "title": "Romantic Warriors: A Progressive Music Saga",
        "poster_url": "https://media.themoviedb.org/t/p/w500/j87Lboh005ChQ8zUijroHQ5fFHJ.jpg",
        "genres": ["Documentary", "Music"],
        "release_year": 2010,
        "runtime": 85,
        "language": "English",
        "country": "USA",
        "overview": "A documentary exploring the history and evolution of progressive rock music.",
        "streaming": []
    },
    {
        "title": "Metal: A Headbanger's Journey",
        "poster_url": "https://vhx.imgix.net/x-streammetal/assets/ba6a8b47-a6e8-4967-aafa-cb9724e01cc5.jpg?auto=format%2Ccompress&fit=crop&h=720&w=1280",
        "genres": ["Documentary", "Music"],
        "release_year": 2005,
        "runtime": 96,
        "language": "English",
        "country": "Canada",
        "overview": "Anthropologist and metal fan Sam Dunn explores the global culture of heavy metal music.",
        "streaming": ["Netflix"]
    },
    {
        "title": "Ballerina",
        "poster_url": "https://image.tmdb.org/t/p/original/vcyohSt5Bx3uDW0FpMBDX2zxpCi.jpg",
        "genres": ["Animation", "Family", "Adventure"],
        "release_year": 2016,
        "runtime": 89,
        "language": "French",
        "country": "France",
        "overview": "An orphan girl dreams of becoming a ballerina and gets a chance to audition for the prestigious Paris Opera Ballet.",
        "streaming": ["Netflix", "Amazon Video", "Apple TV Store", "Fandango At Home"]
    },
    {
        "title": "Terminator 2: Judgment Day",
        "poster_url": "https://kgsmovierants.files.wordpress.com/2015/06/t2-poster.jpg",
        "genres": ["Sci-Fi", "Action", "Adventure"],
        "release_year": 1991,
        "runtime": 137,
        "language": "English",
        "country": "USA",
        "overview": "A cyborg, identical to the one who failed to kill Sarah Connor, must now protect her teenage son, John Connor, from a more advanced and powerful cyborg.",
        "media_franchise": "Terminator",
        "sequel_franchise": "Terminator",
        "streaming": []
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
    
    # Link franchise if exists
    if movie.get("media_franchise") or movie.get("sequel_franchise"):
        # Check if franchise entry exists
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
        print(f"   ↳ Linked franchise: {movie.get('media_franchise')}")
    
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
print("\n✅ All movies added! Backend will reload model on next deploy.")
