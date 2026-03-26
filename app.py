import logging
import os
import sys
import tempfile
from datetime import datetime as _dt
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# ── Structured Logging ──────────────────────────────────────────────────────
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
_log_handlers = [logging.StreamHandler(sys.stdout)]
if not os.getenv("VERCEL"):
    _log_handlers.insert(0, logging.FileHandler(ROOT_DIR / "app.log"))

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, handlers=_log_handlers)
logger = logging.getLogger("CS-DB-Chat")
logger.info("Initializing CS DB Chat Application")

import base64
from dotenv import load_dotenv
load_dotenv(ROOT_DIR / ".env")

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, Response, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from vanna import Agent
from vanna.servers.fastapi.routes import register_chat_routes
from vanna.servers.base import ChatHandler
from vanna.core.user import UserResolver, User, RequestContext

from vanna.integrations.google import GeminiLlmService
from vanna.integrations.openai import OpenAILlmService
from vanna.integrations.cerebras.llm import CerebrasLlmService
from vanna.integrations.ollama import OllamaLlmService
from custom_llm import ResilientLlmService
from vanna.tools import RunSqlTool
from vanna.integrations.postgres import PostgresRunner
from vanna.tools.visualize_data import VisualizeDataTool
from vanna.core.registry import ToolRegistry
from vanna.integrations.chromadb import ChromaAgentMemory
from web_search_tool import WebSearchTool
from vanna.core.system_prompt import DefaultSystemPromptBuilder
from vanna.core.lifecycle import LifecycleHook
from vanna.tools.agent_memory import (
    SaveQuestionToolArgsTool,
    SearchSavedCorrectToolUsesTool,
    SaveTextMemoryTool,
)
from typing import Optional

app = FastAPI(title="CS DB Chat", version="2.4.0")

# ── Middleware ──────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global Exception Handler ────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "An internal server error occurred. Please try again later."},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTP exception: {exc.detail} (status_code={exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

# ── Favicon ──────────────────────────────────────────────────────────────────
# Simple blue chat bubble icon as SVG → served as image/x-icon
_FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
    '<rect width="32" height="32" rx="8" fill="#004ac6"/>'
    '<path d="M8 10h16v10H8z" rx="2" fill="#fff" opacity=".9"/>'
    '<path d="M12 22l-4 3V13h2v7h14v2z" fill="#fff" opacity=".9"/>'
    '</svg>'
)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(content=_FAVICON_SVG.encode(), media_type="image/svg+xml")

# ── User Resolver ────────────────────────────────────────────────────────────
class ProductionUserResolver(UserResolver):
    async def resolve_user(self, request_context: RequestContext) -> User:
        user_email = request_context.get_cookie("vanna_email")
        
        if not user_email:
            # Fallback for system or unauthorized requests
            return User(id="guest", email="guest@example.com", group_memberships=["guest"])
            
        # Determine group memberships
        groups = ["user"]
        
        # Admin check - in production this would be against a DB or OIDC claims
        admin_emails = os.getenv("ADMIN_EMAILS", "admin@example.com").split(",")
        if user_email in admin_emails:
            groups.append("admin")
            
        return User(id=user_email, email=user_email, group_memberships=groups)

# ── Health Check ─────────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    # Get provider health status from LLM service
    provider_health = {}
    if hasattr(llm, 'get_provider_health_status'):
        provider_health = llm.get_provider_health_status()
    
    return JSONResponse(content={
        "status": "healthy",
        "timestamp": _dt.now().isoformat(),
        "version": "2.4.0",
        "providers": provider_health
    })

@app.post("/reset-circuit-breaker/{provider_name}")
async def reset_circuit_breaker(provider_name: str):
    """Reset circuit breaker for a specific provider"""
    if hasattr(llm, 'reset_circuit_breaker'):
        success = llm.reset_circuit_breaker(provider_name)
        if success:
            return JSONResponse(content={
                "message": f"Circuit breaker reset for {provider_name}",
                "timestamp": _dt.now().isoformat()
            })
        else:
            return JSONResponse(
                status_code=404,
                content={"message": f"Provider {provider_name} not found"}
            )
    else:
        return JSONResponse(
            status_code=501,
            content={"message": "Circuit breaker management not available"}
        )

@app.get("/")
async def get_ui():
    return FileResponse(ROOT_DIR / "templates" / "index.html")


providers = []

google_api_key = os.getenv("GOOGLE_API_KEY")
if google_api_key:
    providers.append(
        GeminiLlmService(model=os.getenv("GOOGLE_MODEL", "gemini-2.5-flash"), api_key=google_api_key)
    )

groq_key = os.getenv("GROQ_API_KEY")
if groq_key:
    providers.append(
        OpenAILlmService(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            api_key=groq_key,
            base_url="https://api.groq.com/openai/v1",
            timeout=30.0,
        )
    )

ollama_host = os.getenv("OLLAMA_HOST", "").strip()
if ollama_host:
    providers.append(
        OllamaLlmService(
            model=os.getenv("OLLAMA_MODEL", "glm4:6b"),
            host=ollama_host,
            timeout=30.0,
        )
    )

cerebras_key = os.getenv("CEREBRAS_API_KEY")
if cerebras_key:
    providers.append(
        CerebrasLlmService(
            model=os.getenv("CEREBRAS_MODEL", "llama3.1-8b"),
            api_key=cerebras_key,
            timeout=30.0,
        )
    )

openrouter_key = os.getenv("OPENROUTER_API_KEY")
if openrouter_key:
    providers.append(
        OpenAILlmService(
            model=os.getenv("OPENROUTER_MODEL", "openrouter/free"),
            api_key=openrouter_key,
            base_url="https://openrouter.ai/api/v1",
            timeout=30.0,
        )
    )

if not providers:
    raise RuntimeError(
        "No LLM provider configured. Set at least one of GOOGLE_API_KEY, GROQ_API_KEY, "
        "CEREBRAS_API_KEY, OPENROUTER_API_KEY, or OLLAMA_HOST."
    )

primary_llm = providers[0]
fallbacks = providers[1:]

rpm_limit = int(os.getenv("LLM_RPM_LIMIT", "60"))
if rpm_limit <= 0:
    rpm_limit = 1

llm = ResilientLlmService(
    primary=primary_llm,
    fallbacks=fallbacks,
    rpm_limit=rpm_limit,
)


tools = ToolRegistry()

db_host = os.getenv("DB_HOST", "")
db_port = int(os.getenv("DB_PORT", "5432"))
db_name = os.getenv("DB_NAME", "")
db_user = os.getenv("DB_USER", "")
db_password = os.getenv("DB_PASSWORD", "")
db_sslmode = os.getenv("DB_SSLMODE", "require")
db_connect_timeout = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))
db_statement_timeout_ms = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "30000"))

if all([db_host, db_name, db_user, db_password]):
    tools.register_local_tool(
        RunSqlTool(
            sql_runner=PostgresRunner(
                host=db_host,
                port=db_port,
                database=db_name,
                user=db_user,
                password=db_password,
                sslmode=db_sslmode,
                connect_timeout=db_connect_timeout,
                options=f"-c statement_timeout={db_statement_timeout_ms}",
            )
        ),
        access_groups=["admin", "user"],
    )
else:
    logging.getLogger(__name__).warning(
        "Database environment variables are incomplete; run_sql tool will not be registered."
    )
tools.register_local_tool(WebSearchTool(), access_groups=["admin"])
tools.register_local_tool(VisualizeDataTool(), access_groups=["admin"])
tools.register_local_tool(SaveQuestionToolArgsTool(), access_groups=["admin"])
tools.register_local_tool(
    SearchSavedCorrectToolUsesTool(), access_groups=["admin", "user"]
)
tools.register_local_tool(SaveTextMemoryTool(), access_groups=["admin", "user"])

from vanna.core.system_prompt.default import DefaultSystemPromptBuilder
_today = _dt.now().strftime("%Y-%m-%d")

# ── Custom System Prompt ─────────────────────────────────────────────────────
class CustomSystemPromptBuilder(DefaultSystemPromptBuilder):
    async def build_system_prompt(self, user, tools):
        # 1. Get Vanna's native prompt (which contains essential memory/tool logic)
        prompt = await super().build_system_prompt(user, tools)
        if not prompt: prompt = ""
        
        # 2. Swap the identity name
        prompt = prompt.replace("You are Vanna", "You are CS DB Chat")
        
        # 3. Append our custom routing rules without overriding Vanna's tool instructions
        custom_rules = (
            "\n\nDATABASE CONTEXT:\n"
            "1. The primary table for WooCommerce subscribers is 'woo_subscriptions'. NEVER use 'woo_subscribers'.\n"
            "2. Subscriber tags are stored in 'ontraport_contacts.contact_tags'.\n"
            "3. To query subscribers with specific tags, JOIN 'woo_subscriptions' and 'ontraport_contacts' ON 'email'.\n"
            "\nCRITICAL RULES — FOLLOW EXACTLY:\n"
            "1. You are CS DB Chat. NEVER say you are Vanna.\n"
            "2. For general knowledge, casual chat, math, or weather - answer IMMEDIATELY from your own knowledge. DO NOT use any tools.\n"
            "3. If the user asks about data (Subscriptions, WooCommerce, Ontraport, etc.), USE THE run_sql TOOL.\n"
            "4. After run_sql succeeds, the result will contain a line like: **IMPORTANT: FOR VISUALIZE_DATA USE FILENAME: query_results_XXXXXXXX.csv**. You MUST copy that exact filename when calling visualize_data. NEVER guess or invent a filename.\n"
            "5. If visualize_data returns a file-not-found error, it will list available filenames. Pick one of those — do NOT retry with 'query_results.csv'.\n"
            "6. If you have already retried visualize_data 2 times and still failed, STOP and tell the user: 'The data is ready but I could not generate a chart. Here are the results:' and then summarize the SQL results.\n"
            "7. Keep responses concise and present results in plain English."
        )
        return prompt + custom_rules

agent = Agent(
    llm_service=llm,
    tool_registry=tools,
    user_resolver=ProductionUserResolver(),
    agent_memory=ChromaAgentMemory(
        persist_directory=os.getenv(
            "CHROMA_PERSIST_DIR",
            str(Path(tempfile.gettempdir()) / "cs_db_chat_chroma_memory"),
        ),
        collection_name="cs_db_chat_memories"
    ),
    system_prompt_builder=CustomSystemPromptBuilder(),
    lifecycle_hooks=[],
)

chat_handler = ChatHandler(agent)
register_chat_routes(app, chat_handler)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
