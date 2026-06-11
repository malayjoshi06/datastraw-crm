from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Define the serverless database file path
SQLALCHEMY_DATABASE_URL = "sqlite:///./tickets.db"

# connect_args is required specifically for SQLite to support multi-threading
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency injector to provide a database session to API endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()