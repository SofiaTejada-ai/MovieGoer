import os
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import main

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all the main API routes
app.include_router(main.app, tags=["api"])

# Build and serve the frontend
os.system("cd ../frontend/moviegoerLIVE && npm run build")

# Mount the static files
app.mount("/", StaticFiles(directory="../frontend/moviegoerLIVE/dist", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
