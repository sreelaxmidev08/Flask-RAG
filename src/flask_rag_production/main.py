from fastapi import FastAPI

from flask_rag_production.routes.ask import router as ask_router
from flask_rag_production.routes.search import router as search_router


app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(search_router)
app.include_router(ask_router)