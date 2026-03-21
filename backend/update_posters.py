import psycopg2

DATABASE_URL = "postgresql://postgres:doBjXlXqMXEtvQxvVAQqqqWioUfpCHmh@caboose.proxy.rlwy.net:33590/railway"

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cursor = conn.cursor()

# Fix all movie streaming entries to use correct base_url from streaming_services table
# First update existing entries with placeholder URLs
cursor.execute("""
    UPDATE movie_streaming ms
    SET streaming_url = ss.base_url
    FROM streaming_services ss
    WHERE ms.streaming_service_id = ss.streaming_service_id
    AND ms.streaming_url = 'https://example.com'
""")
print(f"✅ Fixed {cursor.rowcount} entries with placeholder URLs")

# Now add the missing streaming associations
streaming_updates = [
    ("Annabelle: Creation", "Netflix"),
    ("Annabelle: Creation", "Prime Video"),
    ("Cars", "Disney+"),
    ("West Side Story", "Prime Video"),
    ("The Terminator", "Max"),
    ("Braveheart", "Disney+"),
    ("Braveheart", "Prime Video"),
]

for title, service in streaming_updates:
    cursor.execute("SELECT movie_id FROM movies WHERE title = %s", (title,))
    movie = cursor.fetchone()
    if movie:
        movie_id = movie[0]
        cursor.execute("SELECT streaming_service_id, base_url FROM streaming_services WHERE service_name = %s", (service,))
        svc = cursor.fetchone()
        if svc:
            cursor.execute("""INSERT INTO movie_streaming (movie_id, streaming_service_id, streaming_url) 
                              VALUES (%s, %s, %s) ON CONFLICT (movie_id, streaming_service_id) DO UPDATE SET streaming_url = EXCLUDED.streaming_url""", 
                          (movie_id, svc[0], svc[1]))
            print(f"✅ {title} -> {service} ({svc[1]})")
        else:
            print(f"✗ Service '{service}' not found")
    else:
        print(f"✗ Movie '{title}' not found")

print("\n✅ Streaming info added!")
cursor.close()
conn.close()
exit()

# Movies to add
movies_to_add = [
    {
        "title": "Annabelle: Creation",
        "original_title": "Annabelle: Creation",
        "overview": "Twelve years after the tragic death of their daughter, a dollmaker and his wife welcome a nun and several girls from a shuttered orphanage into their home, where they become the target of the dollmaker's possessed creation.",
        "runtime": 109,
        "language": "English",
        "country": "USA",
        "age_rating": "R",
        "average_rating": 3.5,
        "popularity_score": 75.0,
        "poster_url": "https://m.media-amazon.com/images/I/71Cc+vFAsaL.jpg",
        "release_year": 2017,
        "genres": ["Horror", "Thriller"]
    }
]

# Old movies already added - commented out
old_movies = [
    {
        "title": "The Terminator",
        "original_title": "The Terminator",
        "overview": "A cyborg assassin is sent back in time to kill Sarah Connor, whose unborn son will lead humanity against machines.",
        "runtime": 107,
        "language": "English",
        "country": "USA",
        "age_rating": "R",
        "average_rating": 4.1,
        "popularity_score": 85.0,
        "poster_url": "https://m.media-amazon.com/images/I/61sQGAWUOWL.jpg",
        "release_year": 1984,
        "genres": ["Action", "Sci-Fi"]
    },
    {
        "title": "Braveheart",
        "original_title": "Braveheart",
        "overview": "Scottish warrior William Wallace leads his countrymen in a rebellion to free his homeland from the tyranny of King Edward I of England.",
        "runtime": 178,
        "language": "English",
        "country": "USA",
        "age_rating": "R",
        "average_rating": 4.2,
        "popularity_score": 88.0,
        "poster_url": "https://www.themoviedb.org/t/p/original/hS8ydBynxGB9F8QKnv9KeR1jbOj.jpg",
        "release_year": 1995,
        "genres": ["Drama", "War"]
    },
    {
        "title": "Cars",
        "original_title": "Cars",
        "overview": "A hot-shot race car gets stranded in a small town and learns that winning isn't everything in life.",
        "runtime": 117,
        "language": "English",
        "country": "USA",
        "age_rating": "G",
        "average_rating": 3.6,
        "popularity_score": 80.0,
        "poster_url": "https://static1.srcdn.com/wordpress/wp-content/uploads/2024/09/cars-2006-movie-poster.jpg",
        "release_year": 2006,
        "genres": ["Animation", "Comedy"]
    },
    {
        "title": "West Side Story",
        "original_title": "West Side Story",
        "overview": "Two youngsters from rival New York City gangs fall in love, but tensions between their respective friends build toward tragedy.",
        "runtime": 152,
        "language": "English",
        "country": "USA",
        "age_rating": "PG",
        "average_rating": 3.8,
        "popularity_score": 75.0,
        "poster_url": "https://tse3.mm.bing.net/th/id/OIP.ewCBs2u5VW1Ssxk_z7DOKQHaKP?rs=1&pid=ImgDetMain&o=7&rm=3",
        "release_year": 1961,
        "genres": ["Drama", "Musical", "Romance"]
    }
]

for movie in movies_to_add:
    # Insert movie
    cursor.execute("""
        INSERT INTO movies (title, original_title, overview, runtime, language, country, 
                           age_rating, average_rating, popularity_score, poster_url, release_year)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING movie_id
    """, (movie["title"], movie["original_title"], movie["overview"], movie["runtime"],
          movie["language"], movie["country"], movie["age_rating"], movie["average_rating"],
          movie["popularity_score"], movie["poster_url"], movie["release_year"]))
    
    movie_id = cursor.fetchone()[0]
    print(f"✅ Added '{movie['title']}' (ID: {movie_id})")
    
    # Add genres
    for genre_name in movie["genres"]:
        cursor.execute("SELECT genre_id FROM genres WHERE genre_name = %s", (genre_name,))
        genre = cursor.fetchone()
        if genre:
            cursor.execute("INSERT INTO movie_genres (movie_id, genre_id) VALUES (%s, %s)", 
                          (movie_id, genre[0]))
            print(f"   + Genre: {genre_name}")

cursor.close()
conn.close()
print("\n✅ All movies added!")
