import os
import re
import json
import sqlparse
import httpx
import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()

APP_NAME = "KR DATA CHAT"

# --- ENV ---
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free").strip()

# Restrict to ONLY these 2 tables (set real names in env; MVP still works once set)
ALLOWED_TABLES = [
    os.getenv("ALLOWED_TABLE_1", "").strip(),
    os.getenv("ALLOWED_TABLE_2", "").strip(),
]

# --- sanity checks at startup (fail fast) ---
def _startup_check():
    missing = []
    if not DATABASE_URL:
        missing.append("DATABASE_URL")
    if not OPENROUTER_API_KEY:
        missing.append("OPENROUTER_API_KEY")
    if not ALLOWED_TABLES[0]:
        missing.append("ALLOWED_TABLE_1")
    if not ALLOWED_TABLES[1]:
        missing.append("ALLOWED_TABLE_2")
    if missing:
        raise RuntimeError(f"Missing env vars: {', '.join(missing)}")

_startup_check()

app = FastAPI(title=APP_NAME)

class ChatIn(BaseModel):
    message: str

def _validate_sql(sql: str) -> None:
    s = sql.strip()

    # Single statement only, SELECT only
    parsed = sqlparse.parse(s)
    if len(parsed) != 1:
        raise HTTPException(status_code=400, detail="SQL must be a single statement.")
    if not re.match(r"(?is)^select\b", s):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed.")
    if ";" in s:
        raise HTTPException(status_code=400, detail="Semicolons are not allowed.")

    # Must reference only allowed tables (simple but effective MVP gate)
    low = s.lower()
    allowed_low = [t.lower() for t in ALLOWED_TABLES if t]
    if not allowed_low or len(allowed_low) != 2:
        raise HTTPException(status_code=500, detail="Allowed tables not configured.")

    # Extract table-like tokens after FROM/JOIN (basic allowlist)
    candidates = re.findall(r"(?is)\bfrom\s+([a-zA-Z0-9_\.]+)|\bjoin\s+([a-zA-Z0-9_\.]+)", low)
    used = set([c for pair in candidates for c in pair if c])
    if not used:
        raise HTTPException(status_code=400, detail="Query must specify a table.")

    for t in used:
        # allow schema.table matching by suffix too
        ok = any(t == a or t.endswith("." + a) or a.endswith("." + t) for a in allowed_low)
        if not ok:
            raise HTTPException(status_code=403, detail=f"Table not allowed: {t}")

def _run_sql(sql: str):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            cols = [d.name for d in cur.description] if cur.description else []
            rows = cur.fetchall() if cur.description else []
    return cols, rows

async def _openrouter_generate_sql(user_question: str) -> str:
    system = f"""
You are a SQL generator for Postgres.
Rules:
- Output ONLY SQL (no markdown, no explanation).
- Must be ONE statement.
- Must be SELECT only.
- Must query ONLY these two tables: {ALLOWED_TABLES[0]} and {ALLOWED_TABLES[1]}.
- If user asks outside these tables, still return a safe SELECT that explains unavailability via a SELECT literal.
"""

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system.strip()},
            {"role": "user", "content": user_question.strip()}
        ],
        "temperature": 0.1
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        # Optional but recommended by OpenRouter:
        "HTTP-Referer": "https://vercel.com",
        "X-Title": "KR DATA CHAT"
    }

    async with httpx.AsyncClient(timeout=45) as client:
        r = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        if r.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"OpenRouter error: {r.status_code} {r.text}")
        data = r.json()
        sql = data["choices"][0]["message"]["content"]
        return sql.strip()

@app.get("/health")
def health():
    return {"ok": True, "app": APP_NAME}

@app.post("/chat")
async def chat(body: ChatIn):
    sql = await _openrouter_generate_sql(body.message)
    _validate_sql(sql)
    cols, rows = _run_sql(sql)

    # Return in a UI-friendly shape
    return {
        "sql": sql,
        "columns": cols,
        "rows": rows
    }
