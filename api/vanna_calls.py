import os
from dotenv import load_dotenv
from vanna.integrations.google import GeminiLlmService
from vanna.integrations.openai import OpenAI_Chat
from vanna.integrations.postgres import PostgresRunner
from vanna.core.registry import ToolRegistry
from vanna.tools import RunSqlTool
from vanna.core.user import UserResolver, User, RequestContext
from vanna import Agent
from api.auth import verify_token

load_dotenv()

class JwtUserResolver(UserResolver):
    def resolve_user(self, request_context: RequestContext) -> User:
        auth_header = request_context.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            # Reject requests without a valid bearer token
            raise ValueError("Missing or invalid Authorization header")
        
        try:
            token = auth_header.split(" ")[1]
            claims = verify_token(token)
            return User(id=claims.id, email=claims.email, group_memberships=claims.groups)
        except Exception as e:
             # Log the error if possible, but definitely reject the request
             raise ValueError(f"Authentication failed: {str(e)}")

class FallbackLLM:
    def __init__(self, primary, fallback):
        self.primary = primary
        self.fallback = fallback
    
    def __getattr__(self, name):
        if not hasattr(self.primary, name):
            raise AttributeError(f"'{type(self.primary).__name__}' object has no attribute '{name}'")
            
        attr = getattr(self.primary, name)
        if callable(attr):
            def wrapper(*args, **kwargs):
                try:
                    return attr(*args, **kwargs)
                except Exception as e:
                    print(f"Primary LLM error: {e}. Switching to fallback LLM.")
                    if hasattr(self.fallback, name):
                        fallback_attr = getattr(self.fallback, name)
                        return fallback_attr(*args, **kwargs)
                    else:
                        raise e
            return wrapper
        return attr

def setup_vanna():
    # 1. Configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    SUPABASE_CONNECTION_STRING = os.getenv("SUPABASE_CONNECTION_STRING")

    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY environment variable is required")
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY environment variable is required")
    if not SUPABASE_CONNECTION_STRING:
        raise RuntimeError("SUPABASE_CONNECTION_STRING environment variable is required")

    # 2. LLM Services
    # Primary: Gemini 2.5 Flash
    gemini_llm = GeminiLlmService(
        api_key=GEMINI_API_KEY,
        model="gemini-2.0-flash" 
    )

    # Fallback: OpenRouter
    openrouter_llm = OpenAI_Chat(
        api_key=OPENROUTER_API_KEY,
        model="google/gemini-2.0-flash-001",
        client_kwargs={
            "base_url": "https://openrouter.ai/api/v1",
            "default_headers": {
                "HTTP-Referer": "https://vanna.ai",
                "X-Title": "Vanna AI"
            }
        }
    )

    llm_service = FallbackLLM(primary=gemini_llm, fallback=openrouter_llm)

    # 3. Database
    postgres_runner = PostgresRunner(connection_string=SUPABASE_CONNECTION_STRING)

    # 4. Tools
    registry = ToolRegistry()
    registry.register_local_tool(RunSqlTool(postgres_runner), access_groups=["user", "admin"])

    # 5. Agent
    agent = Agent(
        llm_service=llm_service,
        tool_registry=registry,
        user_resolver=JwtUserResolver()
    )
    
    return agent

# Singleton instance
agent = setup_vanna()
