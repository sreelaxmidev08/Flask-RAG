from flask_rag_production.database import engine
from flask_rag_production.models import Base
from flask_rag_production.models.document import Document
from flask_rag_production.models.chunk import Chunk


Base.metadata.create_all(engine)

print("Tables created successfully.")