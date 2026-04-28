import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# ローカルはSQLite、本番（Render）はPostgreSQLを使用
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./training_app.db")

# RenderのPostgreSQL URLは "postgres://" で始まるがSQLAlchemyは "postgresql://" が必要
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLiteの場合のみ check_same_thread=False が必要
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
