from sqlalchemy import create_engine


DATABASE_URL = (
    "postgresql+psycopg://"
    "rag_user:rag_password"
    "@localhost:5432/"
    "flask_rag"
)

engine = create_engine(DATABASE_URL)