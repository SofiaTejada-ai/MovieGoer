-- PostgreSQL Schema for MovieGoer Database
-- Run this script to initialize your Railway PostgreSQL database

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    passwords_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Movies table
CREATE TABLE IF NOT EXISTS movies (
    movie_id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    original_title VARCHAR(255),
    overview TEXT,
    runtime INTEGER,
    language VARCHAR(50),
    country VARCHAR(100),
    age_rating VARCHAR(20),
    average_rating DECIMAL(3,1),
    popularity_score DECIMAL(10,2),
    poster_url TEXT,
    release_year INTEGER NOT NULL
);

-- Genres table
CREATE TABLE IF NOT EXISTS genres (
    genre_id SERIAL PRIMARY KEY,
    genre_name VARCHAR(100) NOT NULL UNIQUE
);

-- Movie-Genres junction table
CREATE TABLE IF NOT EXISTS movie_genres (
    movie_id INTEGER REFERENCES movies(movie_id) ON DELETE CASCADE,
    genre_id INTEGER REFERENCES genres(genre_id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, genre_id)
);

-- Watch History table
CREATE TABLE IF NOT EXISTS watch_history (
    history_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    movie_id INTEGER REFERENCES movies(movie_id) ON DELETE CASCADE,
    watched_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ratings table
CREATE TABLE IF NOT EXISTS ratings (
    rating_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    movie_id INTEGER REFERENCES movies(movie_id) ON DELETE CASCADE,
    score INTEGER CHECK (score >= 1 AND score <= 5),
    rated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, movie_id)
);

-- User Preferences table
CREATE TABLE IF NOT EXISTS user_preferences (
    preference_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    preferred_genre_id INTEGER REFERENCES genres(genre_id),
    preferred_language VARCHAR(50),
    preferred_country VARCHAR(100),
    min_runtime INTEGER,
    max_runtime INTEGER,
    preferred_age_rating VARCHAR(20),
    preference_weight DECIMAL(3,2)
);

-- Streaming Services table
CREATE TABLE IF NOT EXISTS streaming_services (
    streaming_service_id SERIAL PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL,
    logo_url TEXT
);

-- Movie Streaming junction table
CREATE TABLE IF NOT EXISTS movie_streaming (
    movie_id INTEGER REFERENCES movies(movie_id) ON DELETE CASCADE,
    streaming_service_id INTEGER REFERENCES streaming_services(streaming_service_id) ON DELETE CASCADE,
    streaming_url TEXT,
    PRIMARY KEY (movie_id, streaming_service_id)
);

-- Insert default genres
INSERT INTO genres (genre_name) VALUES 
    ('Action'), ('Adventure'), ('Animation'), ('Comedy'), ('Crime'),
    ('Drama'), ('Family'), ('Fantasy'), ('Horror'), ('Music'),
    ('Mystery'), ('Romance'), ('Sci-Fi'), ('Thriller'), ('War')
ON CONFLICT (genre_name) DO NOTHING;
