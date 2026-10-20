# Flask Docs frontend

This is a static HTML, CSS, and vanilla JavaScript client for the existing FastAPI service. It has no frontend package installation or build step.

## Run locally

Start the existing API and its dependencies from the repository root:

```powershell
docker compose up --build -d
```

In a second PowerShell window, serve the frontend:

```powershell
python -m http.server 5500 --directory frontend
```

Open <http://localhost:5500> in a browser. The browser talks to `http://localhost:8000` by default. To use another API base URL, change `DEFAULT_BASE` in `js/api.js` before serving the frontend.

The API permits browser requests from `http://localhost:5500` and `http://127.0.0.1:5500`. Keep this static server on port 5500, or add its exact origin to the `allow_origins` list in `src/flask_rag_production/main.py` and restart the API.

## Notes

- Chat history is stored in this browser's local storage and is never sent to the API.
- Answers and their retrieved sources stream from `GET /stream`. The source event comes from the same retrieval pass as the answer, so citation numbering stays aligned and answer generation is not repeated. **Explore docs** separately uses `GET /search` in hybrid mode.
- **Explore docs** runs a hybrid search and displays API results with their available scores.
- The API base URL is configured in `js/api.js` because this is a static frontend with no injected environment variables.
