import os
import json
import uuid
import google.generativeai as genai
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI
from datetime import datetime

load_dotenv()

pinecone_key = os.getenv("PINECONE_API_KEY")
gemini_key = os.getenv("MOVIE_GOER_API_KEY")
openai_key = os.getenv("OPEN_AI_EMBEDDINGS_KEY")
DATABASE_URL = os.environ.get("DATABASE_PRIVATE_URL") or os.environ.get("DATABASE_PUBLIC_URL", "")

genai.configure(api_key=gemini_key)
pc = Pinecone(api_key=pinecone_key)
movie_index = pc.Index("movie-overviews")
memory_index = pc.Index("luna-memory")

openai_client = OpenAI(api_key=openai_key)

def get_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def create_embedding(text):
    response = openai_client.embeddings.create(
        model="text-embedding-3-large",
        input=text
    )
    return response.data[0].embedding

def search_similar_movies(query, top_k=10):
    query_embedding = create_embedding(query)
    results = movie_index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True
    )
    return results.matches

def get_movie_details(movie_ids):
    if not movie_ids:
        return []
    
    conn = get_connection()
    cursor = conn.cursor()
    
    placeholders = ','.join(['%s'] * len(movie_ids))
    cursor.execute(f"""
        SELECT m.movie_id, m.title, m.poster_url, m.overview, m.release_year,
               m.runtime, m.language, m.average_rating,
               STRING_AGG(DISTINCT g.genre_name, ', ') as genres
        FROM movies m
        LEFT JOIN movie_genres mg ON m.movie_id = mg.movie_id
        LEFT JOIN genres g ON mg.genre_id = g.genre_id
        WHERE m.movie_id IN ({placeholders})
        GROUP BY m.movie_id
    """, movie_ids)
    
    movies = cursor.fetchall()
    conn.close()
    return [dict(m) for m in movies]

def get_user_preferences(user_id):
    if not user_id:
        return None
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT up.preferred_language, up.preferred_country, up.min_runtime, up.max_runtime,
               up.preferred_age_rating, up.preferred_franchise,
               g.genre_name as preferred_genre
        FROM user_preferences up
        LEFT JOIN genres g ON up.preferred_genre_id = g.genre_id
        WHERE up.user_id = %s
    """, (user_id,))
    
    prefs = cursor.fetchall()
    conn.close()
    
    if not prefs:
        return None
    
    genres = [p['preferred_genre'] for p in prefs if p['preferred_genre']]
    franchises = [p['preferred_franchise'] for p in prefs if p['preferred_franchise']]
    
    first = prefs[0]
    return {
        'genres': list(set(genres)),
        'franchises': list(set(franchises)),
        'language': first['preferred_language'],
        'country': first['preferred_country'],
        'min_runtime': first['min_runtime'],
        'max_runtime': first['max_runtime'],
        'age_rating': first['preferred_age_rating']
    }

def save_chat_to_db(user_id, session_id, role, message, movie_ids=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO luna_chats (user_id, session_id, role, message, movie_ids, created_at)
        VALUES (%s, %s, %s, %s, %s, NOW())
        RETURNING chat_id
    """, (user_id, session_id, role, message, movie_ids or []))
    chat_id = cursor.fetchone()['chat_id']
    conn.commit()
    conn.close()
    return chat_id

def save_chat_to_memory(user_id, session_id, role, message):
    embedding = create_embedding(message)
    memory_id = f"{user_id}-{session_id}-{uuid.uuid4().hex[:8]}"
    memory_index.upsert(vectors=[{
        'id': memory_id,
        'values': embedding,
        'metadata': {
            'user_id': str(user_id),
            'session_id': session_id,
            'role': role,
            'message': message[:500],
            'timestamp': datetime.now().isoformat()
        }
    }])

def get_relevant_memories(user_id, query, top_k=5):
    query_embedding = create_embedding(query)
    results = memory_index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
        filter={"user_id": str(user_id)} if user_id else None
    )
    
    memories = []
    for match in results.matches:
        if match.score > 0.7:
            memories.append({
                'role': match.metadata.get('role', 'user'),
                'message': match.metadata.get('message', ''),
                'score': match.score
            })
    return memories

def get_chat_history(user_id, session_id=None, limit=20):
    conn = get_connection()
    cursor = conn.cursor()
    
    if session_id:
        cursor.execute("""
            SELECT chat_id, role, message, movie_ids, created_at
            FROM luna_chats
            WHERE user_id = %s AND session_id = %s
            ORDER BY created_at ASC
            LIMIT %s
        """, (user_id, session_id, limit))
    else:
        cursor.execute("""
            SELECT DISTINCT ON (session_id) session_id, message, created_at
            FROM luna_chats
            WHERE user_id = %s AND role = 'user'
            ORDER BY session_id, created_at DESC
        """, (user_id,))
    
    history = cursor.fetchall()
    conn.close()
    return [dict(h) for h in history]

def get_user_sessions(user_id, limit=10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT session_id, MIN(created_at) as started_at, 
               MAX(created_at) as last_message,
               COUNT(*) as message_count,
               (SELECT message FROM luna_chats lc2 
                WHERE lc2.session_id = lc.session_id AND lc2.role = 'user' 
                ORDER BY created_at ASC LIMIT 1) as first_message
        FROM luna_chats lc
        WHERE user_id = %s
        GROUP BY session_id
        ORDER BY MAX(created_at) DESC
        LIMIT %s
    """, (user_id, limit))
    
    sessions = cursor.fetchall()
    conn.close()
    return [dict(s) for s in sessions]

demo_conversations = {}

def ask_luna(query: str, user_id: int = None, is_demo: bool = False, session_id: str = None):
    print(f"[Luna] user_id={user_id}, is_demo={is_demo}, session_id={session_id}, query={query[:50]}...")
    
    if not session_id:
        session_id = uuid.uuid4().hex
        print(f"[Luna] Generated new session_id: {session_id}")
    
    current_history = []
    
    if user_id and session_id:
        current_history = get_chat_history(user_id, session_id, limit=10)
        print(f"[Luna] Fetched {len(current_history)} messages from DB")
        save_chat_to_db(user_id, session_id, 'user', query)
        save_chat_to_memory(user_id, session_id, 'user', query)
    elif is_demo:
        if session_id not in demo_conversations:
            demo_conversations[session_id] = []
        current_history = demo_conversations[session_id][-10:]
        print(f"[Luna] Demo mode - {len(current_history)} messages in memory")
        demo_conversations[session_id].append({'role': 'user', 'message': query})
    
    similar_movies = search_similar_movies(query, top_k=10)
    
    if not similar_movies:
        response_msg = "I couldn't find any movies matching your request. Try describing what kind of movie you're looking for!"
        if user_id:
            save_chat_to_db(user_id, session_id, 'luna', response_msg)
        return {
            "message": response_msg,
            "movies": [],
            "session_id": session_id
        }
    
    movie_ids = [int(match.id) for match in similar_movies]
    movie_details = get_movie_details(movie_ids)
    
    user_prefs = get_user_preferences(user_id) if user_id else None
    preferences_context = ""
    if user_prefs:
        preferences_context = "\n\nUSER'S MOVIE PREFERENCES (from their profile):\n"
        if user_prefs['genres']:
            preferences_context += f"- Favorite Genres: {', '.join(user_prefs['genres'])}\n"
        if user_prefs['franchises']:
            preferences_context += f"- Favorite Franchises: {', '.join(user_prefs['franchises'])}\n"
        if user_prefs['language']:
            preferences_context += f"- Preferred Language: {user_prefs['language']}\n"
        if user_prefs['age_rating']:
            preferences_context += f"- Age Rating Preference: {user_prefs['age_rating']}\n"
        if user_prefs['min_runtime'] or user_prefs['max_runtime']:
            rt = f"{user_prefs['min_runtime'] or 0}-{user_prefs['max_runtime'] or 999} min"
            preferences_context += f"- Runtime Preference: {rt}\n"
    
    conversation_context = ""
    if current_history:
        conversation_context = "\n\nCURRENT CONVERSATION HISTORY:\n"
        for msg in current_history:
            conversation_context += f"- {msg['role'].upper()}: {msg['message'][:200]}\n"
    
    memory_context = ""
    if user_id:
        memories = get_relevant_memories(user_id, query, top_k=3)
        if memories:
            memory_context = "\n\nRELEVANT PAST CONVERSATIONS (from other sessions):\n"
            for mem in memories:
                memory_context += f"- {mem['role']}: {mem['message']}\n"
    
    movie_list = ""
    for movie in movie_details:
        movie_list += f"- ID:{movie['movie_id']} | \"{movie['title']}\" ({movie['release_year']}) | {movie['genres'] or 'N/A'} | {movie['overview'][:200]}...\n"
    
    prompt = f"""You are Luna, a friendly movie recommendation AI for MovieGoer.
{preferences_context}
{conversation_context}
{memory_context}
User's current message: "{query}"

HERE ARE THE ONLY MOVIES YOU CAN RECOMMEND (from our database):
{movie_list}

STRICT RULES:
1. ONLY recommend movies from the list above - do NOT mention any other movies
2. When mentioning a movie, use EXACTLY this format: **Movie Title** (year)
3. Pick the 3-5 best matches for what the user wants
4. Explain WHY each movie fits their request - consider the USER'S PREFERENCES when explaining
5. IMPORTANT: Read the CURRENT CONVERSATION HISTORY above - remember what the user asked before and your previous responses
6. If the user asks about previous messages, refer to the conversation history
7. Use the USER'S MOVIE PREFERENCES to personalize recommendations - mention if a movie matches their favorite genres or franchises

Return JSON format:
{{
    "message": "Your friendly response using **Movie Title** format for each movie you mention",
    "selected_movie_ids": [list of movie_id integers you recommended]
}}

Be warm and use emojis sparingly!"""

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        
        response_text = response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        result = json.loads(response_text.strip())
        
        selected_ids = result.get("selected_movie_ids", movie_ids[:5])
        selected_movies = [m for m in movie_details if m['movie_id'] in selected_ids]
        
        luna_message = result.get("message", "Here are some movies I think you'll love!")
        
        if user_id:
            save_chat_to_db(user_id, session_id, 'luna', luna_message, selected_ids)
            save_chat_to_memory(user_id, session_id, 'luna', luna_message)
        
        return {
            "message": luna_message,
            "movies": selected_movies,
            "session_id": session_id
        }
        
    except Exception as e:
        print(f"Luna error: {e}")
        fallback_msg = "I found some great movies for you! Here are my top picks based on what you're looking for:"
        if user_id:
            save_chat_to_db(user_id, session_id, 'luna', fallback_msg, movie_ids[:5])
        return {
            "message": fallback_msg,
            "movies": movie_details[:5],
            "session_id": session_id
        }
