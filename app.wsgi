from app.main import app
from app.db.init_db import init_db

# Инициализация базы данных при запуске
init_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 