from sqlalchemy import text

from flask_rag_production.database import engine


with engine.connect() as connection:
    result = connection.execute(text("SELECT 1"))

    print(result.scalar())