import os
from vanna.integrations.google import GeminiLlmService
from vanna.integrations.openai import OpenAI_Chat
from vanna.integrations.postgres import PostgresRunner
from vanna.core.registry import ToolRegistry
from vanna.tools import RunSqlTool
from vanna import Agent

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
        print("Warning: GEMINI_API_KEY not found")
    if not OPENROUTER_API_KEY:
        print("Warning: OPENROUTER_API_KEY not found")
    if not SUPABASE_CONNECTION_STRING:
        print("Warning: SUPABASE_CONNECTION_STRING not found")
        SUPABASE_CONNECTION_STRING = "postgresql://placeholder:placeholder@localhost:5432/placeholder"

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
    registry.register_local_tool(RunSqlTool(postgres_runner), access_groups=[])

    # 5. Agent
    agent = Agent(
        llm_service=llm_service,
        tool_registry=registry,
    )
    
    return agent

# Singleton instance
agent = setup_vanna()
