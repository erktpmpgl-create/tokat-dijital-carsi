import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Kalıcılık: canlıda DATABASE_URL ile /app/data (volume) altına yönlendirilir.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tokat_carsi.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
