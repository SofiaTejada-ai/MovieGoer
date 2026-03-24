import os
import json
import google.generativeai as genai
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure Gemini API
GEMINI_API_KEY = os.environ.get("MOVIE_GOER_API_KEY", "")
genai.configure(api_key=GEMINI_API_KEY)

DATABASE_URL = os.environ.get("DATABASE_URL", "")

def get_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def fetch_user_profile(user_id: int) -> dict:
    """Fetch complete user profile: preferences, franchise preferences, watch history, and ratings."""
    conn = get_connection()
    cursor = conn.cursor()

    # User info
    cursor.execute("SELECT user_id, username FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return None

    # Preferences (genres, language, country, age rating, runtime)
    cursor.execute("""
        SELECT p.preferred_genre_id, g.genre_name, p.preferred_language, p.preferred_country,
               p.min_runtime, p.max_runtime, p.preferred_age_rating, p.preference_weight,
               p.preferred_franchise
        FROM user_preferences p
        LEFT JOIN genres g ON p.preferred_genre_id = g.genre_id
        WHERE p.user_id = %s
        ORDER BY p.preference_weight DESC
    """, (user_id,))
    pref_rows = cursor.fetchall()

    genres = list(set(row["genre_name"] for row in pref_rows if row["genre_name"]))
    franchises = list(set(row["preferred_franchise"] for row in pref_rows if row.get("preferred_franchise")))
    language = next((row["preferred_language"] for row in pref_rows if row["preferred_language"]), None)
    country = next((row["preferred_country"] for row in pref_rows if row["preferred_country"]), None)
    age_rating = next((row["preferred_age_rating"] for row in pref_rows if row["preferred_age_rating"]), None)
    min_runtime = next((row["min_runtime"] for row in pref_rows if row["min_runtime"] is not None), None)
    max_runtime = next((row["max_runtime"] for row in pref_rows if row["max_runtime"] is not None), None)

    # Watch history with movie details and user ratings
    cursor.execute("""
        SELECT m.movie_id, m.title, m.language, m.country, m.age_rating, m.runtime,
               m.release_year, m.average_rating,
               (SELECT STRING_AGG(g.genre_name, ', ')
                FROM movie_genres mg
                JOIN genres g ON mg.genre_id = g.genre_id
                WHERE mg.movie_id = m.movie_id) as genres,
               r.score as user_rating,
               wh.watched_date
        FROM watch_history wh
        JOIN movies m ON wh.movie_id = m.movie_id
        LEFT JOIN ratings r ON r.movie_id = m.movie_id AND r.user_id = wh.user_id
        WHERE wh.user_id = %s
        ORDER BY wh.watched_date DESC
    """, (user_id,))
    history_rows = cursor.fetchall()

    watch_history = []
    seen_ids = set()
    for row in history_rows:
        if row["movie_id"] not in seen_ids:
            seen_ids.add(row["movie_id"])
            watch_history.append({
                "title": row["title"],
                "genres": row["genres"] or "",
                "language": row["language"] or "",
                "country": row["country"] or "",
                "age_rating": row["age_rating"] or "",
                "runtime": row["runtime"],
                "release_year": row["release_year"],
                "user_rating": row["user_rating"],
                "watched_date": str(row["watched_date"]) if row["watched_date"] else None
            })

    conn.close()

    return {
        "user_id": user_id,
        "username": user["username"],
        "preferences": {
            "favorite_genres": genres,
            "favorite_franchises": franchises,
            "preferred_language": language,
            "preferred_country": country,
            "preferred_age_rating": age_rating,
            "min_runtime": min_runtime,
            "max_runtime": max_runtime
        },
        "watch_history": watch_history
    }


def fetch_movie_details(movie_id: int) -> dict:
    """Fetch full movie details including genres and franchise info."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT m.movie_id, m.title, m.original_title, m.overview, m.runtime,
               m.language, m.country, m.age_rating, m.average_rating,
               m.popularity_score, m.release_year,
               (SELECT STRING_AGG(g.genre_name, ', ')
                FROM movie_genres mg
                JOIN genres g ON mg.genre_id = g.genre_id
                WHERE mg.movie_id = m.movie_id) as genres
        FROM movies m
        WHERE m.movie_id = %s
    """, (movie_id,))
    movie = cursor.fetchone()

    if not movie:
        conn.close()
        return None

    # Franchise info
    cursor.execute("""
        SELECT media_franchise, sequel_franchise
        FROM franchises
        WHERE movie_id = %s
    """, (movie_id,))
    franchise_row = cursor.fetchone()

    conn.close()

    return {
        "title": movie["title"],
        "original_title": movie["original_title"],
        "overview": movie["overview"] or "No overview available.",
        "genres": movie["genres"] or "",
        "language": movie["language"] or "",
        "country": movie["country"] or "",
        "age_rating": movie["age_rating"] or "",
        "runtime": movie["runtime"],
        "release_year": movie["release_year"],
        "average_rating": float(movie["average_rating"]) if movie["average_rating"] else None,
        "popularity_score": float(movie["popularity_score"]) if movie["popularity_score"] else None,
        "franchise": franchise_row["media_franchise"] if franchise_row else None,
        "sequel_franchise": franchise_row["sequel_franchise"] if franchise_row else None
    }


def predict_movie_preference(user_id: int, movie_id: int) -> dict:
    """Use Gemini to predict whether a user would like a specific movie."""
    user_profile = fetch_user_profile(user_id)
    if not user_profile:
        return {"error": "User not found"}

    movie = fetch_movie_details(movie_id)
    if not movie:
        return {"error": "Movie not found"}

    prompt = f"""You are MovieGoer AI, a movie recommendation expert. Analyze this user's complete viewing profile and predict whether they would enjoy the target movie.

USER PROFILE:
- Username: {user_profile['username']}
- Favorite Genres: {', '.join(user_profile['preferences']['favorite_genres']) or 'None set'}
- Favorite Franchises: {', '.join(user_profile['preferences']['favorite_franchises']) or 'None set'}
- Preferred Language: {user_profile['preferences']['preferred_language'] or 'No preference'}
- Preferred Country: {user_profile['preferences']['preferred_country'] or 'No preference'}
- Preferred Age Rating: {user_profile['preferences']['preferred_age_rating'] or 'No preference'}
- Runtime Preference: {f"{user_profile['preferences']['min_runtime']}-{user_profile['preferences']['max_runtime']} min" if user_profile['preferences']['min_runtime'] else 'No preference'}

WATCH HISTORY ({len(user_profile['watch_history'])} movies):
{json.dumps(user_profile['watch_history'], indent=2)}

TARGET MOVIE:
{json.dumps(movie, indent=2)}

Based on:
1. How well the movie's genres align with the user's favorite genres
2. Franchise loyalty (does the user follow this franchise?)
3. Language and country preferences
4. Age rating comfort zone
5. Runtime preferences
6. Patterns in their watch history and ratings (what they rated high vs low)
7. The movie's overall quality (average rating, popularity)

Respond ONLY with valid JSON (no markdown, no code fences):
{{
    "prediction": "YES or MAYBE or NO",
    "confidence": 1-10,
    "match_percentage": 0-100,
    "reasoning": "2-3 sentence explanation of why",
    "pros": ["reason they might like it", "another reason"],
    "cons": ["potential concern", "another concern"]
}}"""

    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)

    try:
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = json.loads(text)
    except (json.JSONDecodeError, Exception):
        result = {
            "prediction": "MAYBE",
            "confidence": 5,
            "match_percentage": 50,
            "reasoning": response.text.strip(),
            "pros": [],
            "cons": []
        }

    result["movie_title"] = movie["title"]
    result["user_id"] = user_id
    return result


# Chat sessions stored in memory (keyed by "user_id:movie_id")
_chat_sessions = {}


def chat_about_movie(user_id: int, movie_id: int, message: str) -> dict:
    """Chat with Gemini about a specific movie in the context of the user's profile."""
    session_key = f"{user_id}:{movie_id}"

    if session_key not in _chat_sessions:
        user_profile = fetch_user_profile(user_id)
        movie = fetch_movie_details(movie_id)

        if not user_profile or not movie:
            return {"error": "User or movie not found"}

        system_prompt = f"""You are MovieGoer AI, a friendly and knowledgeable movie expert. You are chatting with {user_profile['username']} about the movie "{movie['title']}".

You have access to their complete profile:
- Favorite Genres: {', '.join(user_profile['preferences']['favorite_genres']) or 'None set'}
- Favorite Franchises: {', '.join(user_profile['preferences']['favorite_franchises']) or 'None set'}
- Preferred Language: {user_profile['preferences']['preferred_language'] or 'No preference'}
- Watch History: {len(user_profile['watch_history'])} movies watched
- Recent movies: {', '.join(m['title'] + (f" (rated {m['user_rating']}/10)" if m['user_rating'] else '') for m in user_profile['watch_history'][:10]) or 'None yet'}

Movie details for "{movie['title']}":
- Genres: {movie['genres']}
- Overview: {movie['overview']}
- Language: {movie['language']}, Country: {movie['country']}
- Age Rating: {movie['age_rating']}, Runtime: {movie['runtime']} min
- Release Year: {movie['release_year']}
- Average Rating: {movie['average_rating']}/10
- Franchise: {movie['franchise'] or 'Standalone'}

Keep responses concise (2-4 sentences), friendly, and personalized to their taste. You can discuss the movie's plot, themes, similar movies they've watched, or anything else they ask. Do NOT use markdown formatting — respond in plain text."""

        model = genai.GenerativeModel("gemini-2.0-flash")
        chat = model.start_chat(history=[
            {"role": "user", "parts": [system_prompt]},
            {"role": "model", "parts": ["Got it! I'm ready to chat about this movie. What would you like to know?"]}
        ])
        _chat_sessions[session_key] = chat

    chat = _chat_sessions[session_key]
    response = chat.send_message(message)

    return {
        "reply": response.text.strip(),
        "movie_id": movie_id,
        "user_id": user_id
    }


def clear_chat_session(user_id: int, movie_id: int):
    """Clear a chat session when the user leaves the movie page."""
    session_key = f"{user_id}:{movie_id}"
    _chat_sessions.pop(session_key, None)
