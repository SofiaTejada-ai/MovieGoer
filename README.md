# MovieGoer

An AI powered movie recommendation platform that blends collaborative filtering with Google Gemini to deliver personalized film discovery, intelligent predictions, and conversational insights about every movie in the catalog.

**Live Demo:** [https://moviegoerlive-production.up.railway.app/](https://moviegoerlive-production.up.railway.app/)

## Overview

MovieGoer is a full stack web application designed to help users discover films tailored to their unique taste. The platform learns from watch history, user preferences, franchise loyalty, and ratings to surface meaningful recommendations. An integrated Gemini 2.0 Flash assistant lets users ask "Would I like this movie?" and receive an evidence backed prediction along with the ability to chat about the film in natural language.

## Features

**Personalized Recommendations**
A hybrid recommendation engine combining content based filtering (TF IDF vectorization and cosine similarity across genres, franchises, runtime, and metadata) with collaborative filtering based on watch history and ratings. A slot reservation strategy ensures a balanced mix of ML derived suggestions and preference matched titles.

**AI Movie Predictions**
Users can click "Is This My Next Favorite?" on any movie page to receive a structured Gemini prediction with a match percentage, confidence score, reasoning, pros, and cons tailored to their full user profile.

**Conversational AI Chat**
Persistent chat sessions let users ask Gemini anything about a movie. The assistant remembers context per user and movie, and personalizes responses using genre preferences, franchise loyalty, and viewing history.

**Franchise Aware Discovery**
Movies are tagged with both media franchise and sequel franchise, allowing the recommender to surface thematically connected titles such as Marvel, Middle earth, Pixar, or The Dark Knight Trilogy.

**Preference Onboarding Quiz**
New users complete a guided quiz covering favorite genres, franchises, language, country, runtime, and age rating. Preferences are weighted and drive both cold start recommendations and long term personalization.

**Streaming Integration**
Every movie is linked to the streaming platforms it is available on (Netflix, Disney+, Max, Prime Video, Apple TV+, and more) with direct watch links.

**Interactive Rating System**
A consistent 0 to 10 rating scale across the entire platform with clickable star ratings, watch history tracking, and user rating persistence.

## Tech Stack

**Frontend:** React, Vite, TailwindCSS, shadcn/ui, Lucide icons, Framer Motion, React Router

**Backend:** FastAPI, Pydantic, psycopg2, Uvicorn

**Database:** PostgreSQL with a normalized schema covering users, movies, genres, franchises, ratings, watch history, preferences, and streaming services

**Machine Learning:** scikit learn (TF IDF, cosine similarity), pandas, NumPy

**AI Integration:** Google Gemini 2.0 Flash via the google generativeai SDK

**Authentication:** Custom authentication with hashed passwords (SHA 256) and session management

## Architecture

The platform is built as a decoupled client server system. The React frontend communicates with a FastAPI backend over REST, which in turn queries PostgreSQL for structured data and calls the Gemini API for LLM features. The recommendation model is loaded into memory at startup and refreshes its feature matrices from the database on demand.

```
MovieGoer/
  backend/
    main.py              FastAPI application and all REST endpoints
    model.py             MovieRecommender class with TF IDF and cosine similarity
    llm_predictor.py     Gemini integration for predictions and chat
    init_postgres.sql    Database schema and seed data
    requirements.txt     Python dependencies
  frontend/
    moviegoerLIVE/       React + Vite single page application
      src/pages/         Route level components (Dashboard, MovieDetail, Login, etc.)
      src/components/    Reusable UI components
      src/lib/api.js     API client
  Dockerfile             Backend container definition
```

## Core Endpoints

```
GET  /movies                              List all movies
GET  /movies/{movie_id}                   Movie detail with genres and streaming
GET  /recommendations/user/{user_id}      Personalized recommendations
POST /ratings                             Submit or update a user rating
POST /watch_history                       Log a watched movie
POST /preferences                         Save user preferences from the quiz
GET  /ai/predict/{user_id}/{movie_id}     Gemini powered prediction
POST /ai/chat                             Send a message to the AI assistant
POST /register, /login, /forgot_password  Authentication flows
```

## Deployment

The backend, PostgreSQL database, and frontend are all deployed on Railway. The backend runs in a Docker container defined by the root `Dockerfile`, while the frontend is served as a Vite production build. Environment variables (database URL, Gemini API key, SMTP credentials, and allowed origins) are managed through Railway's variable system and never committed to the repository.

## Author

Sofia Tejada Sarria
