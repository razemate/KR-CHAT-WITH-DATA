# 01 - Architecture (MVP)

- Next.js frontend in /frontend
- FastAPI backend as Vercel function in /api/index.py
- Frontend calls POST /api/chat
- Backend:
  - OpenRouter generates SQL (SELECT-only)
  - SQL is validated + restricted to 2 allowlisted tables
  - SQL runs on Supabase Postgres and returns rows
