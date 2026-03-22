from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
import os
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from jose import JWTError, jwt
from model import recommender  # v3: War & Documentary movies added

# JWT Configuration
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "moviegoer-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"user_id": int(user_id), "username": payload.get("username"), "email": payload.get("email")}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# Database connection - uses DATABASE_URL from Railway
DATABASE_URL = os.environ.get("DATABASE_URL", "")

def get_connection():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def load_recommender_from_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT movie_id, title, original_title, overview, runtime, language,
               country, age_rating, average_rating, popularity_score,
               poster_url, release_year
        FROM movies
    """)
    movie_rows = cursor.fetchall()
    movies_data = [
        {
            "Movie_id": row["movie_id"],
            "Title": row["title"],
            "Original_Title": row["original_title"],
            "Overview": row["overview"],
            "Runtime": row["runtime"],
            "Language": row["language"],
            "Country": row["country"],
            "Age_Rating": row["age_rating"],
            "Average_Rating": float(row["average_rating"]) if row["average_rating"] is not None else None,
            "Popularity_Score": float(row["popularity_score"]) if row["popularity_score"] is not None else None,
            "Poster_Url": row["poster_url"],
            "Release_Year": row["release_year"]
        }
        for row in movie_rows
    ]

    cursor.execute("""
        SELECT genre_id, genre_name
        FROM genres
    """)
    genre_rows = cursor.fetchall()
    genres_data = [
        {
            "Genre_id": row["genre_id"],
            "Genre_Name": row["genre_name"]
        }
        for row in genre_rows
    ]

    cursor.execute("""
        SELECT movie_id, genre_id
        FROM movie_genres
    """)
    movie_genre_rows = cursor.fetchall()
    movie_genres_data = [
        {
            "Movie_id": row["movie_id"],
            "Genre_id": row["genre_id"]
        }
        for row in movie_genre_rows
    ]

    # Fetch franchise data
    cursor.execute("""
        SELECT movie_id, media_franchise, sequel_franchise
        FROM franchises
    """)
    franchise_rows = cursor.fetchall()
    franchises_data = [
        {
            "Movie_id": row["movie_id"],
            "Media_Franchise": row["media_franchise"],
            "Sequel_Franchise": row["sequel_franchise"]
        }
        for row in franchise_rows
    ]

    conn.close()

    recommender.load_data_from_backend(movies_data, genres_data, movie_genres_data, franchises_data)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        if DATABASE_URL:
            load_recommender_from_db()
            print("✅ Recommender loaded from database")
        else:
            print("⚠️ No DATABASE_URL set - running without database")
    except Exception as e:
        print(f"⚠️ Could not connect to database: {e}")
        print("Server starting without database connection...")
    yield

app = FastAPI(title="MovieGoer API", lifespan=lifespan)

# CORS - add your Railway frontend URL to allowed origins
allowed_origins = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserOut(BaseModel):
    User_id: int
    Username: str
    Email: str

class MovieOut(BaseModel):
    Movie_id: int
    Title: str
    Original_Title: Optional[str] = None
    Overview: Optional[str] = None
    Runtime: Optional[int] = None
    Language: Optional[str] = None
    Country: Optional[str] = None
    Age_Rating: Optional[str] = None
    Average_Rating: Optional[float] = None
    Popularity_Score: Optional[float] = None
    Poster_Url: Optional[str] = None
    Release_Year: int
    Genres: Optional[str] = None
    StreamingServices: Optional[List[dict]] = []

class WatchHistoryIn(BaseModel):
    User_id: int
    Movie_id: int

class RatingIn(BaseModel):
    User_id: int
    Movie_id: int
    Score: int

class PreferenceIn(BaseModel):
    User_id: int
    Preferred_Genre_id: Optional[int] = None
    Preferred_Language: Optional[str] = None
    Preferred_Country: Optional[str] = None
    Min_Runtime: Optional[int] = None
    Max_Runtime: Optional[int] = None
    Preferred_Age_Rating: Optional[str] = None
    Preference_Weight: Optional[float] = None
    Preferred_Franchise: Optional[str] = None

class RegisterIn(BaseModel):
    Username: str
    Email: str
    Password: str

class LoginIn(BaseModel):
    Email: str
    Password: str

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

@app.post("/register")
def register_user(payload: RegisterIn):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id FROM users
            WHERE email = %s OR username = %s
        """, (payload.Email, payload.Username))
        existing = cursor.fetchone()
        if existing:
            conn.close()
            raise HTTPException(status_code=409, detail="Username or email already exists")
        password_hash = hash_password(payload.Password)
        cursor.execute("""
            INSERT INTO users (username, email, passwords_hash)
            VALUES (%s, %s, %s)
            RETURNING user_id
        """, (payload.Username, payload.Email, password_hash))
        new_user = cursor.fetchone()
        conn.commit()
        conn.close()
        return {
            "User_id": new_user["user_id"],
            "Username": payload.Username,
            "Email": payload.Email
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/login")
def login_user(payload: LoginIn):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        password_hash = hash_password(payload.Password)
        cursor.execute("""
            SELECT user_id, username, email
            FROM users
            WHERE email = %s AND passwords_hash = %s
        """, (payload.Email, password_hash))
        user = cursor.fetchone()
        conn.close()
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Create JWT token
        access_token = create_access_token(
            data={"sub": str(user["user_id"]), "username": user["username"], "email": user["email"]}
        )
        
        return {
            "User_id": user["user_id"],
            "Username": user["username"],
            "Email": user["email"],
            "access_token": access_token,
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/auth/me")
def get_current_user(current_user: dict = Depends(verify_token)):
    """Get current user from JWT token"""
    return {
        "User_id": current_user["user_id"],
        "Username": current_user["username"],
        "Email": current_user["email"]
    }

@app.get("/users", response_model=List[UserOut])
def get_users():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, username, email
            FROM users
        """)
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "User_id": row["user_id"],
                "Username": row["username"],
                "Email": row["email"]
            }
            for row in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/movies", response_model=List[MovieOut])
def get_movies():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.movie_id, m.title, m.original_title, m.overview, m.runtime, m.language,
                   m.country, m.age_rating, m.average_rating, m.popularity_score,
                   m.poster_url, m.release_year,
                   (SELECT STRING_AGG(g.genre_name, ', ')
                    FROM movie_genres mg
                    JOIN genres g ON mg.genre_id = g.genre_id
                    WHERE mg.movie_id = m.movie_id) as genres
            FROM movies m
        """)
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "Movie_id": row["movie_id"],
                "Title": row["title"],
                "Original_Title": row["original_title"],
                "Overview": row["overview"],
                "Runtime": row["runtime"],
                "Language": row["language"],
                "Country": row["country"],
                "Age_Rating": row["age_rating"],
                "Average_Rating": float(row["average_rating"]) if row["average_rating"] is not None else None,
                "Popularity_Score": float(row["popularity_score"]) if row["popularity_score"] is not None else None,
                "Poster_Url": row["poster_url"],
                "Release_Year": row["release_year"],
                "Genres": row["genres"] if row["genres"] else ""
            }
            for row in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/movies/search")
def search_movies(query: str):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT movie_id, title, release_year, poster_url, average_rating, language
            FROM movies
            WHERE title ILIKE %s
        """, (f"%{query}%",))
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "Movie_id": row["movie_id"],
                "Title": row["title"],
                "Release_Year": row["release_year"],
                "Poster_Url": row["poster_url"],
                "Average_Rating": float(row["average_rating"]) if row["average_rating"] else None,
                "Language": row["language"]
            }
            for row in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/movies/{movie_id}", response_model=MovieOut)
def get_movie(movie_id: int):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.movie_id, m.title, m.original_title, m.overview, m.runtime, m.language,
                   m.country, m.age_rating, m.average_rating, m.popularity_score,
                   m.poster_url, m.release_year,
                   STRING_AGG(g.genre_name, ', ') as genres
            FROM movies m
            LEFT JOIN movie_genres mg ON m.movie_id = mg.movie_id
            LEFT JOIN genres g ON mg.genre_id = g.genre_id
            WHERE m.movie_id = %s
            GROUP BY m.movie_id, m.title, m.original_title, m.overview, m.runtime, m.language,
                     m.country, m.age_rating, m.average_rating, m.popularity_score,
                     m.poster_url, m.release_year
        """, (movie_id,))
        row = cursor.fetchone()
        
        # Get streaming services for this movie
        streaming_services = []
        try:
            cursor.execute("""
                SELECT s.service_name, s.logo_url, ms.streaming_url
                FROM movie_streaming ms
                JOIN streaming_services s ON ms.streaming_service_id = s.streaming_service_id
                WHERE ms.movie_id = %s
                ORDER BY s.service_name
            """, (movie_id,))
            streaming_rows = cursor.fetchall()
            streaming_services = [
                {
                    "ServiceName": r["service_name"],
                    "LogoUrl": r["logo_url"],
                    "StreamingUrl": r["streaming_url"]
                }
                for r in streaming_rows
            ]
        except Exception as e:
            print(f"Error fetching streaming services: {e}")
        
        if row is None:
            conn.close()
            raise HTTPException(status_code=404, detail="Movie not found")

        result = {
            "Movie_id": row["movie_id"],
            "Title": row["title"],
            "Original_Title": row["original_title"],
            "Overview": row["overview"],
            "Runtime": row["runtime"],
            "Language": row["language"],
            "Country": row["country"],
            "Age_Rating": row["age_rating"],
            "Average_Rating": float(row["average_rating"]) if row["average_rating"] is not None else None,
            "Popularity_Score": float(row["popularity_score"]) if row["popularity_score"] is not None else None,
            "Poster_Url": row["poster_url"],
            "Release_Year": row["release_year"],
            "Genres": row["genres"] if row["genres"] else "",
            "StreamingServices": streaming_services
        }
        
        conn.close()
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/genres")
def get_genres():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT genre_id, genre_name
            FROM genres
        """)
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "Genre_id": row["genre_id"],
                "Genre_Name": row["genre_name"]
            }
            for row in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/franchises")
def get_franchises():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT media_franchise
            FROM franchises
            WHERE media_franchise IS NOT NULL
            ORDER BY media_franchise
        """)
        rows = cursor.fetchall()
        conn.close()
        return [row["media_franchise"] for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/history")
def add_watch_history(payload: WatchHistoryIn):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO watch_history (user_id, movie_id)
            VALUES (%s, %s)
        """, (payload.User_id, payload.Movie_id))
        conn.commit()
        conn.close()
        return {"message": "Watch history added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ratings")
def add_rating(payload: RatingIn):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT rating_id
            FROM ratings
            WHERE user_id = %s AND movie_id = %s
        """, (payload.User_id, payload.Movie_id))
        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                UPDATE ratings
                SET score = %s
                WHERE user_id = %s AND movie_id = %s
            """, (payload.Score, payload.User_id, payload.Movie_id))
        else:
            cursor.execute("""
                INSERT INTO ratings (user_id, movie_id, score)
                VALUES (%s, %s, %s)
            """, (payload.User_id, payload.Movie_id, payload.Score))

        conn.commit()
        conn.close()
        return {"message": "Rating saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{user_id}/history")
def get_user_history(user_id: int):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT wh.movie_id, m.title, m.poster_url, wh.watched_date, r.score as user_rating
            FROM watch_history wh
            JOIN movies m ON wh.movie_id = m.movie_id
            LEFT JOIN ratings r ON wh.movie_id = r.movie_id AND wh.user_id = r.user_id
            WHERE wh.user_id = %s
            ORDER BY wh.watched_date DESC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "Movie_id": row["movie_id"],
                "Title": row["title"],
                "Poster_Url": row["poster_url"],
                "Watched_Date": row["watched_date"],
                "User_Rating": float(row["user_rating"]) if row["user_rating"] else None
            }
            for row in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{user_id}/ratings")
def get_user_ratings(user_id: int):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.movie_id, m.title, m.poster_url, r.score
            FROM ratings r
            JOIN movies m ON r.movie_id = m.movie_id
            WHERE r.user_id = %s
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "Movie_id": row["movie_id"],
                "Title": row["title"],
                "Poster_Url": row["poster_url"],
                "Score": row["score"]
            }
            for row in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/preferences/{user_id}")
def clear_user_preferences(user_id: int):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM user_preferences
            WHERE user_id = %s
        """, (user_id,))
        conn.commit()
        conn.close()
        return {"message": "User preferences cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/preferences")
def add_preference(payload: PreferenceIn):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_preferences
            (user_id, preferred_genre_id, preferred_language, preferred_country,
             min_runtime, max_runtime, preferred_age_rating, preference_weight, preferred_franchise)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            payload.User_id,
            payload.Preferred_Genre_id,
            payload.Preferred_Language,
            payload.Preferred_Country,
            payload.Min_Runtime,
            payload.Max_Runtime,
            payload.Preferred_Age_Rating,
            payload.Preference_Weight,
            payload.Preferred_Franchise
        ))
        conn.commit()
        conn.close()
        return {"message": "Preference saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{user_id}/preferences")
def get_user_preferences(user_id: int):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.preferred_genre_id, g.genre_name, p.preferred_language, p.preferred_country,
                   p.min_runtime, p.max_runtime, p.preferred_age_rating, p.preference_weight
            FROM user_preferences p
            LEFT JOIN genres g ON p.preferred_genre_id = g.genre_id
            WHERE p.user_id = %s
            ORDER BY p.preference_weight DESC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return {"message": "No preferences found"}
        
        first = rows[0]
        genres = [row["genre_name"] for row in rows if row["genre_name"]]
            
        return {
            "Preferred_Genres": genres,
            "Preferred_Language": first["preferred_language"],
            "Preferred_Country": first["preferred_country"],
            "Min_Runtime": first["min_runtime"],
            "Max_Runtime": first["max_runtime"],
            "Preferred_Age_Rating": first["preferred_age_rating"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recommendations/movie/{movie_id}")
def get_recommendations(movie_id: int):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT movie_id, title
            FROM movies
            WHERE movie_id = %s
        """, (movie_id,))
        row = cursor.fetchone()

        if row is None:
            conn.close()
            raise HTTPException(status_code=404, detail="Movie not found")

        result = recommender.get_recommendations_by_id(movie_id)

        if "error" in result:
            conn.close()
            raise HTTPException(status_code=500, detail=result["error"])

        # Fetch fresh poster URLs from database for each recommendation
        recommendations = result["recommendations"]
        if recommendations:
            rec_ids = [rec["Movie_id"] for rec in recommendations]
            placeholders = ",".join(["%s" for _ in rec_ids])
            cursor.execute(f"""
                SELECT movie_id, poster_url, release_year, average_rating
                FROM movies
                WHERE movie_id IN ({placeholders})
            """, rec_ids)
            fresh_data = {r["movie_id"]: r for r in cursor.fetchall()}
            
            # Filter out deleted movies and update with fresh data
            valid_recommendations = []
            for rec in recommendations:
                if rec["Movie_id"] in fresh_data:
                    db_row = fresh_data[rec["Movie_id"]]
                    rec["Poster_Url"] = db_row["poster_url"] if db_row["poster_url"] else ""
                    rec["Release_Year"] = db_row["release_year"]
                    rec["Average_Rating"] = float(db_row["average_rating"]) if db_row["average_rating"] else None
                    valid_recommendations.append(rec)
            recommendations = valid_recommendations

        conn.close()

        return {
            "selected_movie": {
                "Movie_id": row["movie_id"],
                "Title": row["title"]
            },
            "recommendations": recommendations
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def calculate_preference_match_score(movie_row, user_preferences, preferred_genre_ids):
    """
    Calculate score based on actual preference matches
    - Higher score for movies with preferred genres
    - Bonus for matching age rating preference
    - Simple and fast calculation
    """
    movie_genres = set(g.strip() for g in movie_row["genres"].split(", ")) if movie_row["genres"] else set()
    
    # Get user's preferred age rating
    preferred_age_rating = None
    for pref in user_preferences:
        if pref["preferred_age_rating"]:
            preferred_age_rating = pref["preferred_age_rating"]
            break
    
    score = 0.3  # Base score
    
    # Check genre matches - simpler approach
    for pref in user_preferences:
        if pref["preferred_genre_id"] and pref["preferred_genre_id"] in preferred_genre_ids:
            score += 0.2  # 20% bonus per preferred genre
    
    # Age rating bonus
    if preferred_age_rating and movie_row["age_rating"] == preferred_age_rating:
        score += 0.1  # 10% bonus for matching age rating
    
    # Cap at 95%
    return min(score, 0.95)

@app.get("/recommendations/user/{user_id}")
def get_user_recommendations(user_id: int):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get user's watch history with ratings
        cursor.execute("""
            SELECT wh.movie_id, m.title, r.score, wh.watched_date
            FROM watch_history wh
            JOIN movies m ON wh.movie_id = m.movie_id
            LEFT JOIN ratings r ON wh.user_id = r.user_id AND wh.movie_id = r.movie_id
            WHERE wh.user_id = %s
            ORDER BY COALESCE(r.score, 3) DESC, wh.watched_date DESC
        """, (user_id,))
        
        watch_history = cursor.fetchall()
        
        # Cold start: no watch history, use preferences
        if not watch_history:
            cursor.execute("""
                SELECT preferred_genre_id, preferred_language, preferred_country,
                       min_runtime, max_runtime, preferred_age_rating, preference_weight
                FROM user_preferences
                WHERE user_id = %s
                ORDER BY preference_weight DESC
            """, (user_id,))
            
            all_preferences = cursor.fetchall()
            
            if not all_preferences:
                # No preferences either, return popular movies
                cursor.execute("""
                    SELECT m.movie_id, m.title, m.average_rating, m.popularity_score,
                           m.poster_url, m.release_year, m.language, m.country, m.age_rating,
                           STRING_AGG(g.genre_name, ', ') as genres
                    FROM movies m
                    LEFT JOIN movie_genres mg ON m.movie_id = mg.movie_id
                    LEFT JOIN genres g ON mg.genre_id = g.genre_id
                    GROUP BY m.movie_id, m.title, m.average_rating, m.popularity_score,
                             m.poster_url, m.release_year, m.language, m.country, m.age_rating
                    ORDER BY m.popularity_score DESC, m.average_rating DESC
                    LIMIT 10
                """)
                popular_movies = cursor.fetchall()
                conn.close()
                
                return {
                    "user_id": user_id,
                    "recommendation_type": "popular",
                    "recommendations": [
                        {
                            "Movie_id": row["movie_id"],
                            "Title": row["title"],
                            "Poster_Url": row["poster_url"],
                            "Release_Year": row["release_year"],
                            "Average_Rating": float(row["average_rating"]) if row["average_rating"] else None,
                            "Genre_Name": row["genres"] if row["genres"] else "",
                            "Language": row["language"] if row["language"] else "",
                            "Country": row["country"] if row["country"] else "",
                            "Age_Rating": row["age_rating"] if row["age_rating"] else "",
                            "Similarity_Score": 0.5,
                            "Source_Movie": "Popular Movies",
                            "Weight": 0.5
                        }
                        for row in popular_movies
                    ]
                }
            
            # Collect all preferred genre IDs
            genre_ids = [p["preferred_genre_id"] for p in all_preferences if p["preferred_genre_id"]]
            first_pref = all_preferences[0]
            
            # Build flexible query: match ANY preferred genre, soft-filter on other prefs
            where_clauses = []
            params = []
            
            if genre_ids:
                placeholders = ",".join(["%s" for _ in genre_ids])
                where_clauses.append(f"mg.genre_id = ANY (%s)")
                params.append(genre_ids)
            
            if first_pref["preferred_language"]:
                where_clauses.append("m.language = %s")
                params.append(first_pref["preferred_language"])
            
            # Filter R-rated content for child-friendly preferences
            child_friendly_genres = ["Animation", "Family", "Adventure", "Comedy"]
            child_genre_ids = []
            cursor.execute("SELECT genre_id, genre_name FROM genres")
            genre_rows = cursor.fetchall()
            genre_map = {row["genre_name"]: row["genre_id"] for row in genre_rows}
            
            for genre_name in child_friendly_genres:
                if genre_name in genre_map:
                    child_genre_ids.append(genre_map[genre_name])
            
            # If user prefers child-friendly genres, filter out R-rated content
            if any(gid in child_genre_ids for gid in genre_ids):
                where_clauses.append("m.age_rating NOT IN ('R', 'NC-17')")
            
            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            cursor.execute(f"""
                SELECT m.movie_id, m.title, m.language, m.country, m.age_rating,
                       m.poster_url, m.release_year, m.average_rating, m.popularity_score,
                       (SELECT STRING_AGG(g2.genre_name, ', ')
                        FROM movie_genres mg2
                        JOIN genres g2 ON mg2.genre_id = g2.genre_id
                        WHERE mg2.movie_id = m.movie_id) as genres
                FROM movies m
                LEFT JOIN movie_genres mg ON m.movie_id = mg.movie_id
                WHERE {where_clause}
                GROUP BY m.movie_id, m.title, m.language, m.country, m.age_rating,
                         m.poster_url, m.release_year, m.average_rating, m.popularity_score
                ORDER BY m.popularity_score DESC, m.average_rating DESC
                LIMIT 20
            """, params)
            
            preference_movies = cursor.fetchall()
            conn.close()
            
            # Deduplicate by movie_id and calculate scores
            seen = set()
            scored_movies = []
            for row in preference_movies:
                if row["movie_id"] not in seen:
                    seen.add(row["movie_id"])
                    score = calculate_preference_match_score(row, all_preferences, genre_ids)
                    scored_movies.append((row, score))
                if len(scored_movies) >= 10:
                    break
            
            # Sort by score (highest to lowest)
            scored_movies.sort(key=lambda x: x[1], reverse=True)
            unique_movies = [movie for movie, score in scored_movies]
            
            return {
                "user_id": user_id,
                "recommendation_type": "preference_based",
                "recommendations": [
                    {
                        "Movie_id": row["movie_id"],
                        "Title": row["title"],
                        "Poster_Url": row["poster_url"],
                        "Release_Year": row["release_year"],
                        "Average_Rating": float(row["average_rating"]) if row["average_rating"] else None,
                        "Genre_Name": row["genres"] if row["genres"] else "",
                        "Language": row["language"] if row["language"] else "",
                        "Country": row["country"] if row["country"] else "",
                        "Age_Rating": row["age_rating"] if row["age_rating"] else "",
                        "Similarity_Score": round(calculate_preference_match_score(row, all_preferences, genre_ids), 2),
                        "Source_Movie": "Your Preferences",
                        "Weight": 0.7
                    }
                    for row in unique_movies
                ]
            }
        
        # Get user's already watched movie IDs
        watched_movie_ids = {row["movie_id"] for row in watch_history}
        
        # Collect recommendations from user's highest-rated movies
        all_recommendations = {}
        
        # Focus on top 5 highest-rated movies
        top_movies = watch_history[:5]
        
        for movie_row in top_movies:
            movie_id = movie_row["movie_id"]
            
            # Get recommendations for this movie
            movie_recs = recommender.get_recommendations_by_id(movie_id, top_n=10)
            
            if "recommendations" in movie_recs:
                for rec in movie_recs["recommendations"]:
                    rec_movie_id = rec["Movie_id"]
                    
                    # Skip if already watched
                    if rec_movie_id in watched_movie_ids:
                        continue
                    
                    # Add to recommendations with weighted score
                    if rec_movie_id not in all_recommendations:
                        all_recommendations[rec_movie_id] = {
                            "Movie_id": rec["Movie_id"],
                            "Title": rec["Title"],
                            "Genre_Name": rec["Genre_Name"],
                            "Language": rec["Language"],
                            "Country": rec["Country"],
                            "Age_Rating": rec["Age_Rating"],
                            "Poster_Url": rec.get("Poster_Url", ""),
                            "Release_Year": rec.get("Release_Year"),
                            "Average_Rating": rec.get("Average_Rating"),
                            "Similarity_Score": rec["Similarity_Score"],
                            "Source_Movie": movie_row["title"],
                            "Weight": 0
                        }
                    
                    # Weight by user's rating of the source movie
                    user_rating = movie_row["score"] if movie_row["score"] else 3
                    weight_multiplier = user_rating / 5.0  # Normalize to 0-1
                    all_recommendations[rec_movie_id]["Weight"] += rec["Similarity_Score"] * weight_multiplier
        
        # Sort by combined weight
        sorted_recommendations = sorted(
            all_recommendations.values(),
            key=lambda x: x["Weight"],
            reverse=True
        )
        
        # Return top recommendations
        top_recommendations = sorted_recommendations[:10]
        
        conn.close()
        
        return {
            "user_id": user_id,
            "recommendation_type": "collaborative",
            "based_on_movies": [row["title"] for row in top_movies],
            "recommendations": top_recommendations
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))