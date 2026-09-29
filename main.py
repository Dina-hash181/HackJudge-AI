import uvicorn
from src.main import app
from src.config import HOST, PORT

if __name__ == "__main__":
    print(f"Starting DOGFOOD 2026 Platform on http://localhost:{PORT}")
    uvicorn.run("src.main:app", host=HOST, port=PORT, reload=False)
