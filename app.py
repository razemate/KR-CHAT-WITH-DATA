import sys
import os
from pathlib import Path

# Add src to path to ensure vanna is importable
src_path = Path(__file__).parent / "src"
sys.path.append(str(src_path))

from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()

from vanna import Agent
from vanna.core.registry import ToolRegistry
from vanna.servers.fastapi import VannaFastAPIServer
from vanna.integrations.google import GeminiLlmService
from vanna.integrations.openai import OpenAI_Chat
from vanna.integrations.postgres import PostgresRunner
from vanna.tools import RunSqlTool

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SUPABASE_CONNECTION_STRING = os.getenv("SUPABASE_CONNECTION_STRING")

if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not found in .env")
if not OPENROUTER_API_KEY:
    print("Warning: OPENROUTER_API_KEY not found in .env")
if not SUPABASE_CONNECTION_STRING:
    print("Warning: SUPABASE_CONNECTION_STRING not found in .env")
    # Placeholder for safety to avoid crash on init if just testing LLM
    SUPABASE_CONNECTION_STRING = "postgresql://placeholder:placeholder@localhost:5432/placeholder"

# Initialize LLM Services
gemini_llm = GeminiLlmService(
    api_key=GEMINI_API_KEY,
    model="gemini-2.0-flash" # Assuming flash or pro, user provided key for Gemini
)

# OpenRouter uses OpenAI client but with custom base URL
openrouter_llm = OpenAI_Chat(
    api_key=OPENROUTER_API_KEY,
    model="google/gemini-2.0-flash-001", # Example OpenRouter model
    client_kwargs={
        "base_url": "https://openrouter.ai/api/v1",
        "default_headers": {
            "HTTP-Referer": "https://vanna.ai",
            "X-Title": "Vanna AI"
        }
    }
)

# Fallback Mechanism
class FallbackLLM:
    def __init__(self, primary, fallback):
        self.primary = primary
        self.fallback = fallback
    
    def __getattr__(self, name):
        # Delegate all attribute access to primary, but wrap callable methods to handle failure
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

# Use the fallback wrapper
llm_service = FallbackLLM(primary=gemini_llm, fallback=openrouter_llm)

# Initialize Database Runner
# Note: PostgresRunner requires valid connection string to work properly
postgres_runner = PostgresRunner(connection_string=SUPABASE_CONNECTION_STRING)

# Initialize Tool Registry
registry = ToolRegistry()
registry.register_local_tool(RunSqlTool(postgres_runner), access_groups=[])

# Create Agent
agent = Agent(
    llm_service=llm_service,
    tool_registry=registry,
    # Add other components like agent_memory, user_resolver if needed
)

# Create FastAPI Server
server = VannaFastAPIServer(agent)
app = server.create_app()

if __name__ == "__main__":
    print("Starting Vanna Server...")
    print(f"Using Gemini Key: {GEMINI_API_KEY[:5]}...")
    print(f"Using OpenRouter Key: {OPENROUTER_API_KEY[:5]}...")
    server.run(host="0.0.0.0", port=8000)
