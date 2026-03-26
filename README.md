# KR Chat With Data

Serverless FastAPI deployment of the CS DB Chat app for Vercel.

## Stack

- FastAPI backend served from `api/index.py`
- Local `src/vanna` package bundled in-repo
- Static chat UI served from `templates/index.html`
- Vercel routing all requests to the FastAPI app

## Required Environment Variables

- `GOOGLE_API_KEY` or another supported LLM provider key
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`

## Optional Environment Variables

- `GROQ_API_KEY`
- `CEREBRAS_API_KEY`
- `OPENROUTER_API_KEY`
- `OLLAMA_HOST`
- `SERPAPI_KEY`
- `ADMIN_EMAILS`
- `CHROMA_PERSIST_DIR`

## Local Run

```bash
uvicorn app:app --reload
```

## Deploy

```bash
vercel --prod
```
