Review the entire appimport os
from dotenv import load_dotenv
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
            raise ValueError("Missing or invalid Authorization header")

        try:
            token = auth_header.split(" ")[1]
            claims = verify_token(token)
            return User(id=claims.id, email=claims.email, group_memberships=claims.groups)
        except Exception:
            raise ValueError("Authentication failed")


def setup_vanna():
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    SUPABASE_CONNECTION_STRING = os.getenv("SUPABASE_CONNECTION_STRING")

    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY environment variable is required")
    if not SUPABASE_CONNECTION_STRING:
        raise RuntimeError("SUPABASE_CONNECTION_STRING environment variable is required")

    llm_service = OpenAI_Chat(
        api_key=OPENROUTER_API_KEY,
        model="google/gemini-2.0-flash-001",
        client_kwargs={
            "base_url": "https://openrouter.ai/api/v1",
            "default_headers": {
                "HTTP-Referer": "https://vanna.ai",
                "X-Title": "Vanna AI",
            },
        },
    )

    postgres_runner = PostgresRunner(connection_string=SUPABASE_CONNECTION_STRING)

    registry = ToolRegistry()
    registry.register_local_tool(RunSqlTool(postgres_runner), access_groups=["user", "admin"])

    agent = Agent(
        llm_service=llm_service,
        tool_registry=registry,
        user_resolver=JwtUserResolver(),
    )

    return agent


agent = setup_vanna()
