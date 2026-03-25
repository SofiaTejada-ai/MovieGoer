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
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import smtplib
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from model import recommender  # Load recommender model on startup - updated with international movies rating system
from llm_predictor import predict_movie_preference, chat_about_movie, clear_chat_session

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

# Database connection - prefer private URL to avoid egress fees
DATABASE_URL = os.environ.get("DATABASE_PRIVATE_URL") or os.environ.get("DATABASE_URL", "")

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
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
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
    Audience_Reception: Optional[str] = None
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

class ChatMessageIn(BaseModel):
    user_id: int
    movie_id: int
    message: str

class ForgotPasswordIn(BaseModel):
    Email: str

class ResetPasswordIn(BaseModel):
    Token: str
    NewPassword: str

# Password reset token configuration
password_reset_serializer = URLSafeTimedSerializer(SECRET_KEY)
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

# Email configuration
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL", "noreply@moviegoer.app")
SMTP_FALLBACK_PORT = int(os.environ.get("SMTP_FALLBACK_PORT", "2525"))

def send_password_reset_email(to_email: str, reset_link: str):
    """Send password reset email"""
    print(f"📧 Attempting to send email to {to_email}")
    print(f"   SMTP_SERVER: {SMTP_SERVER}")
    print(f"   SMTP_PORT: {SMTP_PORT}")
    print(f"   SMTP_USERNAME: {SMTP_USERNAME[:3]}...{SMTP_USERNAME[-10:] if len(SMTP_USERNAME) > 13 else SMTP_USERNAME}")
    print(f"   SMTP_PASSWORD set: {bool(SMTP_PASSWORD)}")
    
    # DNS resolution test
    try:
        ip_addresses = socket.getaddrinfo(SMTP_SERVER, SMTP_PORT)
        print(f"   DNS resolved: {ip_addresses[0][4][0]}")
    except Exception as dns_err:
        print(f"   ❌ DNS resolution failed: {dns_err}")
    
    # Socket connectivity test
    try:
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_sock.settimeout(5)
        test_sock.connect((SMTP_SERVER, SMTP_PORT))
        test_sock.close()
        print(f"   ✅ Socket connection successful")
    except Exception as sock_err:
        print(f"   ❌ Socket connection failed: {sock_err}")
    
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print(f"⚠️ Email not configured. Reset link for {to_email}: {reset_link}")
        return True  # Return True so flow continues in dev mode
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset Your MovieGoer Password"
    msg["From"] = SMTP_FROM_EMAIL
    msg["To"] = to_email
    
    html = f"""
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0a0a0a; color: #fafafa; padding: 40px;">
        <div style="max-width: 500px; margin: 0 auto; background-color: #171717; border-radius: 16px; padding: 40px; border: 1px solid #262626;">
            <div style="text-align: center; margin-bottom: 30px;">
                <div style="width: 56px; height: 56px; background-color: #7c3aed; border-radius: 12px; display: inline-flex; align-items: center; justify-content: center;">
                    <span style="font-size: 24px;">🎬</span>
                </div>
            </div>
            <h1 style="color: #fafafa; text-align: center; margin-bottom: 20px; font-size: 24px;">Reset Your Password</h1>
            <p style="color: #a1a1aa; text-align: center; margin-bottom: 30px;">
                We received a request to reset your MovieGoer password. Click the button below to create a new password.
            </p>
            <div style="text-align: center; margin-bottom: 30px;">
                <a href="{reset_link}" style="display: inline-block; background-color: #7c3aed; color: white; padding: 14px 32px; border-radius: 12px; text-decoration: none; font-weight: 600;">
                    Reset Password
                </a>
            </div>
            <p style="color: #71717a; text-align: center; font-size: 14px;">
                This link will expire in 1 hour. If you didn't request this, you can safely ignore this email.
            </p>
        </div>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(html, "html"))
    
    ports_to_try = [SMTP_PORT, SMTP_FALLBACK_PORT] if SMTP_FALLBACK_PORT != SMTP_PORT else [SMTP_PORT]
    
    for port in ports_to_try:
        try:
            print(f"   Trying SMTP on port {port}...")
            if port == 465:
                with smtplib.SMTP_SSL(SMTP_SERVER, port, timeout=10) as server:
                    server.login(SMTP_USERNAME, SMTP_PASSWORD)
                    server.sendmail(SMTP_FROM_EMAIL, to_email, msg.as_string())
            else:
                with smtplib.SMTP(SMTP_SERVER, port, timeout=10) as server:
                    server.starttls()
                    server.login(SMTP_USERNAME, SMTP_PASSWORD)
                    server.sendmail(SMTP_FROM_EMAIL, to_email, msg.as_string())
            print(f"✅ Password reset email sent to {to_email} (port {port})")
            return True
        except Exception as e:
            print(f"   ❌ Port {port} failed: {e}")
            continue
    
    print(f"❌ All SMTP ports failed for {to_email}")
    return False

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
        
        # Create JWT token on registration too
        access_token = create_access_token(
            data={"sub": str(new_user["user_id"]), "username": payload.Username, "email": payload.Email}
        )
        
        return {
            "User_id": new_user["user_id"],
            "Username": payload.Username,
            "Email": payload.Email,
            "access_token": access_token,
            "token_type": "bearer"
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

@app.post("/forgot-password")
def forgot_password(payload: ForgotPasswordIn):
    """Request password reset - sends email with reset link"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, email FROM users WHERE email = %s", (payload.Email,))
        user = cursor.fetchone()
        conn.close()
        
        # Always return success to prevent email enumeration attacks
        if user is None:
            return {"message": "If an account with that email exists, a password reset link has been sent."}
        
        # Generate secure token (valid for 1 hour)
        token = password_reset_serializer.dumps(payload.Email, salt="password-reset")
        reset_link = f"{FRONTEND_URL}/reset-password?token={token}"
        
        # Send email
        send_password_reset_email(payload.Email, reset_link)
        
        return {"message": "If an account with that email exists, a password reset link has been sent."}
    except Exception as e:
        print(f"Forgot password error: {e}")
        return {"message": "If an account with that email exists, a password reset link has been sent."}

@app.post("/reset-password")
def reset_password(payload: ResetPasswordIn):
    """Reset password using token from email"""
    try:
        # Verify token (1 hour = 3600 seconds)
        email = password_reset_serializer.loads(payload.Token, salt="password-reset", max_age=3600)
    except SignatureExpired:
        raise HTTPException(status_code=400, detail="Reset link has expired. Please request a new one.")
    except BadSignature:
        raise HTTPException(status_code=400, detail="Invalid reset link.")
    
    # Validate password
    if len(payload.NewPassword) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        password_hash = hash_password(payload.NewPassword)
        cursor.execute("""
            UPDATE users SET passwords_hash = %s WHERE email = %s
        """, (password_hash, email))
        
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="User not found.")
        
        conn.commit()
        conn.close()
        return {"message": "Password has been reset successfully. You can now log in with your new password."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/verify-reset-token")
def verify_reset_token(token: str):
    """Verify if a reset token is still valid"""
    try:
        email = password_reset_serializer.loads(token, salt="password-reset", max_age=3600)
        return {"valid": True, "email": email}
    except SignatureExpired:
        raise HTTPException(status_code=400, detail="Reset link has expired.")
    except BadSignature:
        raise HTTPException(status_code=400, detail="Invalid reset link.")

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
                   m.poster_url, m.release_year, m.audience_reception,
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
                "Genres": row["genres"] if row["genres"] else "",
                "Audience_Reception": row["audience_reception"]
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
                   m.poster_url, m.release_year, m.audience_reception,
                   STRING_AGG(g.genre_name, ', ') as genres
            FROM movies m
            LEFT JOIN movie_genres mg ON m.movie_id = mg.movie_id
            LEFT JOIN genres g ON mg.genre_id = g.genre_id
            WHERE m.movie_id = %s
            GROUP BY m.movie_id, m.title, m.original_title, m.overview, m.runtime, m.language,
                     m.country, m.age_rating, m.average_rating, m.popularity_score,
                     m.poster_url, m.release_year, m.audience_reception
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
            "Audience_Reception": row["audience_reception"],
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
    print(f"📊 Rating request: User={payload.User_id}, Movie={payload.Movie_id}, Score={payload.Score}")
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
                   p.min_runtime, p.max_runtime, p.preferred_age_rating, p.preference_weight,
                   p.preferred_franchise
            FROM user_preferences p
            LEFT JOIN genres g ON p.preferred_genre_id = g.genre_id
            WHERE p.user_id = %s
            ORDER BY p.preference_weight DESC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return {"message": "No preferences found"}
        
        genres = [row["genre_name"] for row in rows if row["genre_name"]]
        franchises = [row["preferred_franchise"] for row in rows if row.get("preferred_franchise")]
        
        # Find first row with actual preference data (not franchise-only rows)
        lang = next((row["preferred_language"] for row in rows if row["preferred_language"]), None)
        ctry = next((row["preferred_country"] for row in rows if row["preferred_country"]), None)
        min_rt = next((row["min_runtime"] for row in rows if row["min_runtime"] is not None), None)
        max_rt = next((row["max_runtime"] for row in rows if row["max_runtime"] is not None), None)
        age_r = next((row["preferred_age_rating"] for row in rows if row["preferred_age_rating"]), None)
            
        return {
            "Preferred_Genres": genres,
            "Preferred_Franchises": franchises,
            "Preferred_Language": lang,
            "Preferred_Country": ctry,
            "Min_Runtime": min_rt,
            "Max_Runtime": max_rt,
            "Preferred_Age_Rating": age_r
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
            ORDER BY COALESCE(r.score, 5) DESC, wh.watched_date DESC
        """, (user_id,))
        
        watch_history = cursor.fetchall()
        
        # Cold start: no watch history, use preferences
        if not watch_history:
            cursor.execute("""
                SELECT preferred_genre_id, preferred_language, preferred_country,
                       min_runtime, max_runtime, preferred_age_rating, preference_weight,
                       preferred_franchise
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
            
            # Collect preferred franchises and genre IDs
            franchise_names = list(set(p["preferred_franchise"] for p in all_preferences if p.get("preferred_franchise")))
            genre_ids = [p["preferred_genre_id"] for p in all_preferences if p["preferred_genre_id"]]
            pref_language = next((p["preferred_language"] for p in all_preferences if p["preferred_language"]), None)
            
            # Build child-friendly filter
            child_friendly_genres = ["Animation", "Family", "Adventure", "Comedy"]
            cursor.execute("SELECT genre_id, genre_name FROM genres")
            genre_rows = cursor.fetchall()
            genre_map = {row["genre_name"]: row["genre_id"] for row in genre_rows}
            child_genre_ids = [genre_map[g] for g in child_friendly_genres if g in genre_map]
            filter_r_rated = any(gid in child_genre_ids for gid in genre_ids)
            
            seen_ids = set()
            final_recommendations = []
            
            # === STEP 1: Franchise movies FIRST ===
            if franchise_names:
                franchise_placeholders = ",".join(["%s"] * len(franchise_names))
                franchise_query = f"""
                    SELECT m.movie_id, m.title, m.language, m.country, m.age_rating,
                           m.poster_url, m.release_year, m.average_rating, m.popularity_score,
                           (SELECT STRING_AGG(g2.genre_name, ', ')
                            FROM movie_genres mg2
                            JOIN genres g2 ON mg2.genre_id = g2.genre_id
                            WHERE mg2.movie_id = m.movie_id) as genres,
                           f.media_franchise
                    FROM movies m
                    JOIN franchises f ON m.movie_id = f.movie_id
                    WHERE f.media_franchise IN ({franchise_placeholders})
                """
                franchise_params = list(franchise_names)
                
                if filter_r_rated:
                    franchise_query += " AND m.age_rating NOT IN ('R', 'NC-17')"
                
                franchise_query += " ORDER BY m.popularity_score DESC, m.average_rating DESC LIMIT 15"
                
                cursor.execute(franchise_query, franchise_params)
                franchise_movies = cursor.fetchall()
                
                for row in franchise_movies:
                    if row["movie_id"] not in seen_ids:
                        seen_ids.add(row["movie_id"])
                        final_recommendations.append({
                            "Movie_id": row["movie_id"],
                            "Title": row["title"],
                            "Poster_Url": row["poster_url"],
                            "Release_Year": row["release_year"],
                            "Average_Rating": float(row["average_rating"]) if row["average_rating"] else None,
                            "Genre_Name": row["genres"] if row["genres"] else "",
                            "Language": row["language"] if row["language"] else "",
                            "Country": row["country"] if row["country"] else "",
                            "Age_Rating": row["age_rating"] if row["age_rating"] else "",
                            "Similarity_Score": 0.90,
                            "Source_Movie": f"Franchise: {row['media_franchise']}",
                            "Weight": 0.95
                        })
            
            # === STEP 2: Fill remaining slots with genre matches ===
            remaining = 10 - len(final_recommendations)
            if remaining > 0 and genre_ids:
                genre_where = ["mg.genre_id = ANY (%s)"]
                genre_params = [genre_ids]
                
                if pref_language:
                    genre_where.append("m.language = %s")
                    genre_params.append(pref_language)
                
                if filter_r_rated:
                    genre_where.append("m.age_rating NOT IN ('R', 'NC-17')")
                
                # Exclude already recommended movies
                if seen_ids:
                    genre_where.append("m.movie_id != ALL(%s)")
                    genre_params.append(list(seen_ids))
                
                genre_clause = " AND ".join(genre_where)
                
                cursor.execute(f"""
                    SELECT DISTINCT m.movie_id, m.title, m.language, m.country, m.age_rating,
                           m.poster_url, m.release_year, m.average_rating, m.popularity_score,
                           (SELECT STRING_AGG(g2.genre_name, ', ')
                            FROM movie_genres mg2
                            JOIN genres g2 ON mg2.genre_id = g2.genre_id
                            WHERE mg2.movie_id = m.movie_id) as genres
                    FROM movies m
                    LEFT JOIN movie_genres mg ON m.movie_id = mg.movie_id
                    WHERE {genre_clause}
                    ORDER BY m.popularity_score DESC, m.average_rating DESC
                    LIMIT %s
                """, genre_params + [remaining + 5])
                
                genre_movies = cursor.fetchall()
                
                for row in genre_movies:
                    if row["movie_id"] not in seen_ids and len(final_recommendations) < 10:
                        seen_ids.add(row["movie_id"])
                        score = calculate_preference_match_score(row, all_preferences, genre_ids)
                        final_recommendations.append({
                            "Movie_id": row["movie_id"],
                            "Title": row["title"],
                            "Poster_Url": row["poster_url"],
                            "Release_Year": row["release_year"],
                            "Average_Rating": float(row["average_rating"]) if row["average_rating"] else None,
                            "Genre_Name": row["genres"] if row["genres"] else "",
                            "Language": row["language"] if row["language"] else "",
                            "Country": row["country"] if row["country"] else "",
                            "Age_Rating": row["age_rating"] if row["age_rating"] else "",
                            "Similarity_Score": round(score, 2),
                            "Source_Movie": "Your Preferences",
                            "Weight": 0.7
                        })
            
            conn.close()
            
            return {
                "user_id": user_id,
                "recommendation_type": "preference_based",
                "recommendations": final_recommendations
            }
        
        # Get user's already watched movie IDs
        watched_movie_ids = {row["movie_id"] for row in watch_history}
        
        # Fetch user preferences to blend into collaborative recommendations
        cursor.execute("""
            SELECT p.preferred_genre_id, g.genre_name, p.preferred_language, p.preferred_country,
                   p.min_runtime, p.max_runtime, p.preferred_age_rating, p.preference_weight,
                   p.preferred_franchise
            FROM user_preferences p
            LEFT JOIN genres g ON p.preferred_genre_id = g.genre_id
            WHERE p.user_id = %s
            ORDER BY p.preference_weight DESC
        """, (user_id,))
        user_prefs = cursor.fetchall()
        
        # Build preference lookup for boosting
        pref_genre_ids = set()
        pref_language = None
        pref_country = None
        pref_age_rating = None
        pref_min_runtime = None
        pref_max_runtime = None
        pref_franchises = set()
        for p in user_prefs:
            if p["preferred_genre_id"]:
                pref_genre_ids.add(p["preferred_genre_id"])
            if p["preferred_language"] and not pref_language:
                pref_language = p["preferred_language"]
            if p["preferred_country"] and not pref_country:
                pref_country = p["preferred_country"]
            if p["preferred_age_rating"] and not pref_age_rating:
                pref_age_rating = p["preferred_age_rating"]
            if p["min_runtime"] is not None and pref_min_runtime is None:
                pref_min_runtime = p["min_runtime"]
            if p["max_runtime"] is not None and pref_max_runtime is None:
                pref_max_runtime = p["max_runtime"]
            if p.get("preferred_franchise"):
                pref_franchises.add(p["preferred_franchise"])
        
        has_prefs = bool(user_prefs)
        
        # Collect recommendations from user's highest-rated movies
        all_recommendations = {}
        
        # Focus on top 5 highest-rated movies
        top_movies = watch_history[:5]
        
        for movie_row in top_movies:
            movie_id = movie_row["movie_id"]
            
            # Get more candidates so preference filtering has room to work
            movie_recs = recommender.get_recommendations_by_id(movie_id, top_n=20 if has_prefs else 10)
            
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
        
        if has_prefs:
            # === SLOT RESERVATION: Split top 10 between ML and preference-matched movies ===
            # This guarantees changing preferences visibly changes the recommendations
            
            # SLOTS 1-5: Top ML collaborative recommendations (from watch history)
            ml_sorted = sorted(all_recommendations.values(), key=lambda x: x["Weight"], reverse=True)
            ml_top = ml_sorted[:5]
            
            # SLOTS 6-10: Fresh movies matching user's current preferences from DB
            all_used_ids = watched_movie_ids | {r["Movie_id"] for r in ml_top}
            exclude_ids = list(all_used_ids)
            exclude_ph = ",".join(["%s"] * len(exclude_ids))
            
            pref_movies = []
            
            # First try franchise matches
            if pref_franchises:
                fran_ph = ",".join(["%s"] * len(pref_franchises))
                fran_list = list(pref_franchises)
                cursor.execute(f"""
                    SELECT DISTINCT m.movie_id, m.title, m.language, m.country, m.age_rating,
                           m.poster_url, m.release_year, m.average_rating, m.popularity_score,
                           (SELECT STRING_AGG(g2.genre_name, ', ')
                            FROM movie_genres mg2
                            JOIN genres g2 ON mg2.genre_id = g2.genre_id
                            WHERE mg2.movie_id = m.movie_id) as genres
                    FROM movies m
                    JOIN franchises f ON m.movie_id = f.movie_id
                    WHERE f.media_franchise IN ({fran_ph})
                      AND m.movie_id NOT IN ({exclude_ph})
                    ORDER BY m.popularity_score DESC, m.average_rating DESC
                    LIMIT 5
                """, fran_list + exclude_ids)
                pref_movies.extend(cursor.fetchall())
            
            # Fill remaining preference slots with genre matches
            remaining = 5 - len(pref_movies)
            if remaining > 0 and pref_genre_ids:
                already_ids = list(all_used_ids | {r["movie_id"] for r in pref_movies})
                already_ph = ",".join(["%s"] * len(already_ids))
                cursor.execute(f"""
                    SELECT DISTINCT m.movie_id, m.title, m.language, m.country, m.age_rating,
                           m.poster_url, m.release_year, m.average_rating, m.popularity_score,
                           (SELECT STRING_AGG(g2.genre_name, ', ')
                            FROM movie_genres mg2
                            JOIN genres g2 ON mg2.genre_id = g2.genre_id
                            WHERE mg2.movie_id = m.movie_id) as genres
                    FROM movies m
                    JOIN movie_genres mg ON m.movie_id = mg.movie_id
                    WHERE mg.genre_id = ANY(%s)
                      AND m.movie_id NOT IN ({already_ph})
                    ORDER BY m.popularity_score DESC, m.average_rating DESC
                    LIMIT %s
                """, [list(pref_genre_ids)] + already_ids + [remaining])
                pref_movies.extend(cursor.fetchall())
            
            # Build preference slot recommendations
            pref_recs = []
            for row in pref_movies[:5]:
                pref_recs.append({
                    "Movie_id": row["movie_id"],
                    "Title": row["title"],
                    "Genre_Name": row["genres"] if row["genres"] else "",
                    "Language": row["language"] if row["language"] else "",
                    "Country": row["country"] if row["country"] else "",
                    "Age_Rating": row["age_rating"] if row["age_rating"] else "",
                    "Poster_Url": row["poster_url"] if row["poster_url"] else "",
                    "Release_Year": row["release_year"],
                    "Average_Rating": float(row["average_rating"]) if row["average_rating"] else None,
                    "Similarity_Score": 0.80,
                    "Source_Movie": "Your Preferences",
                    "Weight": ml_top[-1]["Weight"] if ml_top else 1.0
                })
            
            top_recommendations = sorted(ml_top + pref_recs, key=lambda x: x["Similarity_Score"], reverse=True)
        else:
            # No preferences — pure collaborative filtering
            sorted_recommendations = sorted(
                all_recommendations.values(),
                key=lambda x: x["Weight"],
                reverse=True
            )
            top_recommendations = sorted_recommendations[:10]
        
        conn.close()
        
        return {
            "user_id": user_id,
            "recommendation_type": "preference_collaborative" if has_prefs else "collaborative",
            "based_on_movies": [row["title"] for row in top_movies],
            "recommendations": top_recommendations
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# DELETE ALL USER DATA ENDPOINT
# ============================================

@app.delete("/users/{user_id}/data")
def delete_all_user_data(user_id: int):
    """Permanently delete all user data: preferences, watch history, and ratings"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Delete user preferences
        cursor.execute("""
            DELETE FROM user_preferences
            WHERE user_id = %s
        """, (user_id,))
        
        # Delete watch history
        cursor.execute("""
            DELETE FROM watch_history
            WHERE user_id = %s
        """, (user_id,))
        
        # Delete ratings
        cursor.execute("""
            DELETE FROM ratings
            WHERE user_id = %s
        """, (user_id,))
        
        # Verify deletion by counting remaining records
        cursor.execute("""
            SELECT 
                (SELECT COUNT(*) FROM user_preferences WHERE user_id = %s) as pref_count,
                (SELECT COUNT(*) FROM watch_history WHERE user_id = %s) as hist_count,
                (SELECT COUNT(*) FROM ratings WHERE user_id = %s) as rating_count
        """, (user_id, user_id, user_id))
        
        counts = cursor.fetchone()
        
        conn.commit()
        conn.close()
        
        # Double-check that all data was deleted
        if counts["pref_count"] > 0 or counts["hist_count"] > 0 or counts["rating_count"] > 0:
            raise HTTPException(status_code=500, detail="Failed to delete all user data")
        
        return {
            "message": "All user data permanently deleted",
            "deleted_items": {
                "preferences": True,
                "watch_history": True,
                "ratings": True
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# AI PREDICTION ENDPOINTS (Gemini)
# ============================================

@app.get("/ai/predict/{user_id}/{movie_id}")
def ai_predict_movie(user_id: int, movie_id: int):
    """Predict whether a user would like a specific movie using Gemini AI."""
    try:
        result = predict_movie_preference(user_id, movie_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/chat")
def ai_chat_movie(payload: ChatMessageIn):
    """Chat with Gemini AI about a specific movie, personalized to the user."""
    try:
        result = chat_about_movie(payload.user_id, payload.movie_id, payload.message)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/ai/chat/{user_id}/{movie_id}")
def ai_clear_chat(user_id: int, movie_id: int):
    """Clear a chat session when the user leaves the movie page."""
    clear_chat_session(user_id, movie_id)
    return {"message": "Chat session cleared"}