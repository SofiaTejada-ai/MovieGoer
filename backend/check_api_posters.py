import urllib.request
import json

# Check first 10 movies
url = "http://localhost:8000/movies"
try:
    resp = urllib.request.urlopen(url)
    data = json.loads(resp.read().decode())
    print("First 10 movies from API:")
    for movie in data[:10]:
        print(f"{movie['Movie_id']}: {movie['Title']} - Poster: {'YES' if movie.get('Poster_Url') else 'NO'}")
        if movie.get('Poster_Url'):
            print(f"  URL: {movie['Poster_Url'][:50]}...")
except Exception as e:
    print(f"Error: {e}")
