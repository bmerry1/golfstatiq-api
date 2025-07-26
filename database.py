from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base # Import Base from models.py

# Using SQLite for this example as specified
SQLALCHEMY_DATABASE_URL = "sqlite:///./golfstatiq.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the database tables
def create_db_and_tables():
    Base.metadata.create_all(bind=engine)

# Dependency to get a DB session in API endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()