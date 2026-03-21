from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import pyodbc
import hashlib
from contextlib import asynccontextmanager
from model import recommender

CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=(localdb)\\ProjectModels;"
    "DATABASE=MovieGoerDatabase;"
    "Trusted_Connection=yes;"
)

def get_connection():
    return pyodbc.connect(CONNECTION_STRING)

def load_recommender_from_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT Movie_id, Title, Original_Title, Overview, Runtime, Language,
               Country, Age_Rating, Average_Rating, Popularity_Score,
               Poster_Url, Release_Year
        FROM [MoviesSchema].[MoviesTable]
    """)
    movie_rows = cursor.fetchall()
    movies_data = [
        {
            "Movie_id": row.Movie_id,
            "Title": row.Title,
            "Original_Title": row.Original_Title,
            "Overview": row.Overview,
            "Runtime": row.Runtime,
            "Language": row.Language,
            "Country": row.Country,
            "Age_Rating": row.Age_Rating,
            "Average_Rating": float(row.Average_Rating) if row.Average_Rating is not None else None,
            "Popularity_Score": float(row.Popularity_Score) if row.Popularity_Score is not None else None,
            "Poster_Url": row.Poster_Url,
            "Release_Year": row.Release_Year
        }
        for row in movie_rows
    ]

    cursor.execute("""
        SELECT Genre_id, Genre_Name
        FROM [GenreSchema].[GenreTable]
    """)
    genre_rows = cursor.fetchall()
    genres_data = [
        {
            "Genre_id": row.Genre_id,
            "Genre_Name": row.Genre_Name
        }
        for row in genre_rows
    ]

    cursor.execute("""
        SELECT Movie_id, Genre_id
        FROM [GenreSchema].[MovieGenresTable]
    """)
    movie_genre_rows = cursor.fetchall()
    movie_genres_data = [
        {
            "Movie_id": row.Movie_id,
            "Genre_id": row.Genre_id
        }
        for row in movie_genre_rows
    ]

    conn.close()

    recommender.load_data_from_backend(movies_data, genres_data, movie_genres_data)

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_recommender_from_db()
    yield

app = FastAPI(title="MovieGoer API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
            SELECT User_id FROM [UserSchema].[UserTable]
            WHERE Email = ? OR Username = ?
        """, (payload.Email, payload.Username))
        existing = cursor.fetchone()
        if existing:
            conn.close()
            raise HTTPException(status_code=409, detail="Username or email already exists")
        password_hash = hash_password(payload.Password)
        cursor.execute("""
            INSERT INTO [UserSchema].[UserTable] (Username, Email, Passwords_hash)
            OUTPUT INSERTED.User_id
            VALUES (?, ?, ?)
        """, (payload.Username, payload.Email, password_hash))
        new_user = cursor.fetchone()
        conn.commit()
        conn.close()
        return {
            "User_id": new_user.User_id,
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
            SELECT User_id, Username, Email
            FROM [UserSchema].[UserTable]
            WHERE Email = ? AND Passwords_hash = ?
        """, (payload.Email, password_hash))
        user = cursor.fetchone()
        conn.close()
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        return {
            "User_id": user.User_id,
            "Username": user.Username,
            "Email": user.Email
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users", response_model=List[UserOut])
def get_users():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT User_id, Username, Email
            FROM [UserSchema].[UserTable]
        """)
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "User_id": row.User_id,
                "Username": row.Username,
                "Email": row.Email
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
            SELECT m.Movie_id, m.Title, m.Original_Title, m.Overview, m.Runtime, m.Language,
                   m.Country, m.Age_Rating, m.Average_Rating, m.Popularity_Score,
                   m.Poster_Url, m.Release_Year,
                   (SELECT STRING_AGG(g.Genre_Name, ', ')
                    FROM [GenreSchema].[MovieGenresTable] mg
                    JOIN [GenreSchema].[GenreTable] g ON mg.Genre_id = g.Genre_id
                    WHERE mg.Movie_id = m.Movie_id) as Genres
            FROM [MoviesSchema].[MoviesTable] m
        """)
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "Movie_id": row.Movie_id,
                "Title": row.Title,
                "Original_Title": row.Original_Title,
                "Overview": row.Overview,
                "Runtime": row.Runtime,
                "Language": row.Language,
                "Country": row.Country,
                "Age_Rating": row.Age_Rating,
                "Average_Rating": float(row.Average_Rating) if row.Average_Rating is not None else None,
                "Popularity_Score": float(row.Popularity_Score) if row.Popularity_Score is not None else None,
                "Poster_Url": row.Poster_Url,
                "Release_Year": row.Release_Year,
                "Genres": row.Genres if row.Genres else ""
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
            SELECT Movie_id, Title, Release_Year, Poster_Url, Average_Rating, Language
            FROM [MoviesSchema].[MoviesTable]
            WHERE Title LIKE ?
        """, (f"%{query}%",))
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "Movie_id": row.Movie_id,
                "Title": row.Title,
                "Release_Year": row.Release_Year,
                "Poster_Url": row.Poster_Url,
                "Average_Rating": float(row.Average_Rating) if row.Average_Rating else None,
                "Language": row.Language
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
            SELECT m.Movie_id, m.Title, m.Original_Title, m.Overview, m.Runtime, m.Language,
                   m.Country, m.Age_Rating, m.Average_Rating, m.Popularity_Score,
                   m.Poster_Url, m.Release_Year,
                   STRING_AGG(g.Genre_Name, ', ') as Genres
            FROM [MoviesSchema].[MoviesTable] m
            LEFT JOIN [GenreSchema].[MovieGenresTable] mg ON m.Movie_id = mg.Movie_id
            LEFT JOIN [GenreSchema].[GenreTable] g ON mg.Genre_id = g.Genre_id
            WHERE m.Movie_id = ?
            GROUP BY m.Movie_id, m.Title, m.Original_Title, m.Overview, m.Runtime, m.Language,
                     m.Country, m.Age_Rating, m.Average_Rating, m.Popularity_Score,
                     m.Poster_Url, m.Release_Year
        """, (movie_id,))
        row = cursor.fetchone()
        
        # Get streaming services for this movie
        try:
            cursor.execute("""
                SELECT s.ServiceName, s.LogoUrl, ms.StreamingUrl
                FROM [StreamingSchema].[MovieStreamingTable] ms
                JOIN [StreamingSchema].[StreamingServicesTable] s ON ms.StreamingService_id = s.StreamingService_id
                WHERE ms.Movie_id = ?
                ORDER BY s.ServiceName
            """, (movie_id,))
            streaming_rows = cursor.fetchall()
        except Exception as e:
            print(f"Error fetching streaming services: {e}")
            streaming_rows = []
        
        streaming_services = [
            {
                "ServiceName": row.ServiceName,
                "LogoUrl": row.LogoUrl,
                "StreamingUrl": row.StreamingUrl
            }
            for row in streaming_rows
        ]
        
        if row is None:
            conn.close()
            raise HTTPException(status_code=404, detail="Movie not found")

        result = {
            "Movie_id": row.Movie_id,
            "Title": row.Title,
            "Original_Title": row.Original_Title,
            "Overview": row.Overview,
            "Runtime": row.Runtime,
            "Language": row.Language,
            "Country": row.Country,
            "Age_Rating": row.Age_Rating,
            "Average_Rating": float(row.Average_Rating) if row.Average_Rating is not None else None,
            "Popularity_Score": float(row.Popularity_Score) if row.Popularity_Score is not None else None,
            "Poster_Url": row.Poster_Url,
            "Release_Year": row.Release_Year,
            "Genres": row.Genres if row.Genres else "",
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
            SELECT Genre_id, Genre_Name
            FROM [GenreSchema].[GenreTable]
        """)
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "Genre_id": row.Genre_id,
                "Genre_Name": row.Genre_Name
            }
            for row in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/history")
def add_watch_history(payload: WatchHistoryIn):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO [WatchHistorySchema].[WatchHistoryTable] (User_id, Movie_id)
            VALUES (?, ?)
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
            SELECT Rating_id
            FROM [RatingsSchema].[RatingsTable]
            WHERE User_id = ? AND Movie_id = ?
        """, (payload.User_id, payload.Movie_id))
        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                UPDATE [RatingsSchema].[RatingsTable]
                SET Score = ?
                WHERE User_id = ? AND Movie_id = ?
            """, (payload.Score, payload.User_id, payload.Movie_id))
        else:
            cursor.execute("""
                INSERT INTO [RatingsSchema].[RatingsTable] (User_id, Movie_id, Score)
                VALUES (?, ?, ?)
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
            SELECT wh.Movie_id, m.Title, wh.Watched_Date
            FROM [WatchHistorySchema].[WatchHistoryTable] wh
            JOIN [MoviesSchema].[MoviesTable] m ON wh.Movie_id = m.Movie_id
            WHERE wh.User_id = ?
            ORDER BY wh.Watched_Date DESC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "Movie_id": row.Movie_id,
                "Title": row.Title,
                "Watched_Date": row.Watched_Date
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
            SELECT r.Movie_id, m.Title, r.Score
            FROM [RatingsSchema].[RatingsTable] r
            JOIN [MoviesSchema].[MoviesTable] m ON r.Movie_id = m.Movie_id
            WHERE r.User_id = ?
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "Movie_id": row.Movie_id,
                "Title": row.Title,
                "Score": row.Score
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
            DELETE FROM [PreferenceSchema].[UserPreferenceTable]
            WHERE User_id = ?
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
            INSERT INTO [PreferenceSchema].[UserPreferenceTable]
            (User_id, Preferred_Genre_id, Preferred_Language, Preferred_Country,
             Min_Runtime, Max_Runtime, Preferred_Age_Rating, Preference_Weight)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payload.User_id,
            payload.Preferred_Genre_id,
            payload.Preferred_Language,
            payload.Preferred_Country,
            payload.Min_Runtime,
            payload.Max_Runtime,
            payload.Preferred_Age_Rating,
            payload.Preference_Weight
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
            SELECT p.Preferred_Genre_id, g.Genre_Name, p.Preferred_Language, p.Preferred_Country,
                   p.Min_Runtime, p.Max_Runtime, p.Preferred_Age_Rating, p.Preference_Weight
            FROM [PreferenceSchema].[UserPreferenceTable] p
            LEFT JOIN [GenreSchema].[GenreTable] g ON p.Preferred_Genre_id = g.Genre_id
            WHERE p.User_id = ?
            ORDER BY p.Preference_Weight DESC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return {"message": "No preferences found"}
        
        first = rows[0]
        genres = [row.Genre_Name for row in rows if row.Genre_Name]
            
        return {
            "Preferred_Genres": genres,
            "Preferred_Language": first.Preferred_Language,
            "Preferred_Country": first.Preferred_Country,
            "Min_Runtime": first.Min_Runtime,
            "Max_Runtime": first.Max_Runtime,
            "Preferred_Age_Rating": first.Preferred_Age_Rating
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recommendations/movie/{movie_id}")
def get_recommendations(movie_id: int):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Movie_id, Title
            FROM [MoviesSchema].[MoviesTable]
            WHERE Movie_id = ?
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
            placeholders = ",".join(["?" for _ in rec_ids])
            cursor.execute(f"""
                SELECT Movie_id, Poster_Url, Release_Year, Average_Rating
                FROM [MoviesSchema].[MoviesTable]
                WHERE Movie_id IN ({placeholders})
            """, rec_ids)
            fresh_data = {r.Movie_id: r for r in cursor.fetchall()}
            
            for rec in recommendations:
                if rec["Movie_id"] in fresh_data:
                    db_row = fresh_data[rec["Movie_id"]]
                    rec["Poster_Url"] = db_row.Poster_Url if db_row.Poster_Url else ""
                    rec["Release_Year"] = db_row.Release_Year
                    rec["Average_Rating"] = float(db_row.Average_Rating) if db_row.Average_Rating else None

        conn.close()

        return {
            "selected_movie": {
                "Movie_id": row.Movie_id,
                "Title": row.Title
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
    movie_genres = set(g.strip() for g in movie_row.Genres.split(", ")) if movie_row.Genres else set()
    
    # Get user's preferred age rating
    preferred_age_rating = None
    for pref in user_preferences:
        if pref.Preferred_Age_Rating:
            preferred_age_rating = pref.Preferred_Age_Rating
            break
    
    score = 0.3  # Base score
    
    # Check genre matches - simpler approach
    for pref in user_preferences:
        if pref.Preferred_Genre_id and pref.Preferred_Genre_id in preferred_genre_ids:
            # Simple genre match check without extra query
            score += 0.2  # 20% bonus per preferred genre
    
    # Age rating bonus
    if preferred_age_rating and movie_row.Age_Rating == preferred_age_rating:
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
            SELECT wh.Movie_id, m.Title, r.Score, wh.Watched_Date
            FROM [WatchHistorySchema].[WatchHistoryTable] wh
            JOIN [MoviesSchema].[MoviesTable] m ON wh.Movie_id = m.Movie_id
            LEFT JOIN [RatingsSchema].[RatingsTable] r ON wh.User_id = r.User_id AND wh.Movie_id = r.Movie_id
            WHERE wh.User_id = ?
            ORDER BY COALESCE(r.Score, 3) DESC, wh.Watched_Date DESC
        """, (user_id,))
        
        watch_history = cursor.fetchall()
        
        # Cold start: no watch history, use preferences
        if not watch_history:
            cursor.execute("""
                SELECT Preferred_Genre_id, Preferred_Language, Preferred_Country,
                       Min_Runtime, Max_Runtime, Preferred_Age_Rating, Preference_Weight
                FROM [PreferenceSchema].[UserPreferenceTable]
                WHERE User_id = ?
                ORDER BY Preference_Weight DESC
            """, (user_id,))
            
            all_preferences = cursor.fetchall()
            
            if not all_preferences:
                # No preferences either, return popular movies
                cursor.execute("""
                    SELECT TOP 10 m.Movie_id, m.Title, m.Average_Rating, m.Popularity_Score,
                           m.Poster_Url, m.Release_Year, m.Language, m.Country, m.Age_Rating,
                           STRING_AGG(g.Genre_Name, ', ') as Genres
                    FROM [MoviesSchema].[MoviesTable] m
                    LEFT JOIN [GenreSchema].[MovieGenresTable] mg ON m.Movie_id = mg.Movie_id
                    LEFT JOIN [GenreSchema].[GenreTable] g ON mg.Genre_id = g.Genre_id
                    GROUP BY m.Movie_id, m.Title, m.Average_Rating, m.Popularity_Score,
                             m.Poster_Url, m.Release_Year, m.Language, m.Country, m.Age_Rating
                    ORDER BY m.Popularity_Score DESC, m.Average_Rating DESC
                """)
                popular_movies = cursor.fetchall()
                conn.close()
                
                return {
                    "user_id": user_id,
                    "recommendation_type": "popular",
                    "recommendations": [
                        {
                            "Movie_id": row.Movie_id,
                            "Title": row.Title,
                            "Poster_Url": row.Poster_Url,
                            "Release_Year": row.Release_Year,
                            "Average_Rating": float(row.Average_Rating) if row.Average_Rating else None,
                            "Genre_Name": row.Genres if row.Genres else "",
                            "Language": row.Language if row.Language else "",
                            "Country": row.Country if row.Country else "",
                            "Age_Rating": row.Age_Rating if row.Age_Rating else "",
                            "Similarity_Score": 0.5,
                            "Source_Movie": "Popular Movies",
                            "Weight": 0.5
                        }
                        for row in popular_movies
                    ]
                }
            
            # Collect all preferred genre IDs
            genre_ids = [p.Preferred_Genre_id for p in all_preferences if p.Preferred_Genre_id]
            first_pref = all_preferences[0]
            
            # Build flexible query: match ANY preferred genre, soft-filter on other prefs
            where_clauses = []
            params = []
            
            if genre_ids:
                placeholders = ",".join(["?" for _ in genre_ids])
                where_clauses.append(f"mg.Genre_id IN ({placeholders})")
                params.extend(genre_ids)
            
            if first_pref.Preferred_Language:
                where_clauses.append("m.Language = ?")
                params.append(first_pref.Preferred_Language)
            
            # Filter R-rated content for child-friendly preferences
            child_friendly_genres = ["Animation", "Family", "Adventure", "Comedy"]
            child_genre_ids = []
            cursor.execute("SELECT Genre_id, Genre_Name FROM [GenreSchema].[GenreTable]")
            genre_rows = cursor.fetchall()
            genre_map = {row.Genre_Name: row.Genre_id for row in genre_rows}
            
            for genre_name in child_friendly_genres:
                if genre_name in genre_map:
                    child_genre_ids.append(genre_map[genre_name])
            
            # If user prefers child-friendly genres, filter out R-rated content
            if any(gid in child_genre_ids for gid in genre_ids):
                where_clauses.append("m.Age_Rating NOT IN ('R', 'NC-17')")
            
            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            cursor.execute(f"""
                SELECT TOP 20 m.Movie_id, m.Title, m.Language, m.Country, m.Age_Rating,
                       m.Poster_Url, m.Release_Year, m.Average_Rating, m.Popularity_Score,
                       (SELECT STRING_AGG(g2.Genre_Name, ', ')
                        FROM [GenreSchema].[MovieGenresTable] mg2
                        JOIN [GenreSchema].[GenreTable] g2 ON mg2.Genre_id = g2.Genre_id
                        WHERE mg2.Movie_id = m.Movie_id) as Genres
                FROM [MoviesSchema].[MoviesTable] m
                LEFT JOIN [GenreSchema].[MovieGenresTable] mg ON m.Movie_id = mg.Movie_id
                WHERE {where_clause}
                GROUP BY m.Movie_id, m.Title, m.Language, m.Country, m.Age_Rating,
                         m.Poster_Url, m.Release_Year, m.Average_Rating, m.Popularity_Score
                ORDER BY m.Popularity_Score DESC, m.Average_Rating DESC
            """, params)
            
            preference_movies = cursor.fetchall()
            conn.close()
            
            # Deduplicate by Movie_id and calculate scores
            seen = set()
            scored_movies = []
            for row in preference_movies:
                if row.Movie_id not in seen:
                    seen.add(row.Movie_id)
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
                        "Movie_id": row.Movie_id,
                        "Title": row.Title,
                        "Poster_Url": row.Poster_Url,
                        "Release_Year": row.Release_Year,
                        "Average_Rating": float(row.Average_Rating) if row.Average_Rating else None,
                        "Genre_Name": row.Genres if row.Genres else "",
                        "Language": row.Language if row.Language else "",
                        "Country": row.Country if row.Country else "",
                        "Age_Rating": row.Age_Rating if row.Age_Rating else "",
                        "Similarity_Score": round(calculate_preference_match_score(row, all_preferences, genre_ids), 2),
                        "Source_Movie": "Your Preferences",
                        "Weight": 0.7
                    }
                    for row in unique_movies
                ]
            }
        
        # Get user's already watched movie IDs
        watched_movie_ids = {row.Movie_id for row in watch_history}
        
        # Collect recommendations from user's highest-rated movies
        all_recommendations = {}
        
        # Focus on top 5 highest-rated movies
        top_movies = watch_history[:5]
        
        for movie_row in top_movies:
            movie_id = movie_row.Movie_id
            
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
                            "Source_Movie": movie_row.Title,
                            "Weight": 0
                        }
                    
                    # Weight by user's rating of the source movie
                    user_rating = movie_row.Score if movie_row.Score else 3
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
            "based_on_movies": [row.Title for row in top_movies],
            "recommendations": top_recommendations
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))