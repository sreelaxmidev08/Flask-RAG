from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from flask_rag_production.routes.ask import router as ask_router
from flask_rag_production.routes.search import router as search_router


app = FastAPI()

# Local static frontend origins served with `python -m http.server 5500`.
# Keep this list explicit so the development API does not accept arbitrary sites.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(search_router)
app.include_router(ask_router)
