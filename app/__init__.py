from app.core.config import settings
from app.db.database import Base, engine

# Создаем таблицы при импорте
Base.metadata.create_all(bind=engine)
