import os
os.environ["DATABASE_URL"] = "postgresql://postgres:REDACTED@caboose.proxy.rlwy.net:33590/railway"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174"

import uvicorn
uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
