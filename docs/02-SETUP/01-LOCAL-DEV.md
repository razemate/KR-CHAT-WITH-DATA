# 02 - Setup

Local:
- Backend runs via: python -m uvicorn api.index:app --reload
- Frontend runs via: cd frontend ; npm run dev

Prod (Vercel):
- Push to GitHub
- Vercel builds Next.js and serves /api as Python runtime
