# Production Deployment Guide: CS DB Chat

This guide outlines the steps to deploy the CS DB Chat application to a production environment.

## 1. Environment Variables

Create a `.env` file in the root directory with the following variables:

### LLM Configuration (Required)
- `GOOGLE_API_KEY`: Your Google AI API key for Gemini 2.5 Flash.
- `GROQ_API_KEY`: (Optional) Fallback LLM.
- `CEREBRAS_API_KEY`: (Optional) Fallback LLM.
- `OPENROUTER_API_KEY`: (Optional) Fallback LLM.
- `LLM_RPM_LIMIT`: (Default: 60) Rate limit for LLM calls.

### Database Configuration (Postgres)
- `DB_HOST`: Host address of your Postgres database.
- `DB_PORT`: (Default: 5432) Port of your Postgres database.
- `DB_NAME`: Name of your database.
- `DB_USER`: Username for database access.
- `DB_PASSWORD`: Password for database access.
- `DB_SSLMODE`: (Default: require) SSL mode for connection.
- `DB_CONNECT_TIMEOUT`: (Default: 10) Connection timeout in seconds.
- `DB_STATEMENT_TIMEOUT_MS`: (Default: 30000) Statement timeout in milliseconds.

### Tooling (Optional)
- `SERPAPI_KEY`: Required for the `WebSearchTool`.

### Authentication
- `ADMIN_EMAILS`: (Default: admin@example.com) Comma-separated list of admin email addresses.

## 2. Persistence

The app uses `ChromaAgentMemory` for persistent storage of chat history and agent memory.
- By default, it persists to the `./chroma_memory` directory.
- Ensure the application process has write permissions to this directory.

## 3. Running the Application

### Using Uvicorn (Development/Testing)
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

### Using Gunicorn (Production)
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0:8000
```

## 4. Health Check

The application provides a health check endpoint at `/health`.

```bash
curl http://localhost:8000/health
```

## 5. UI Customization

The UI is served from `templates/index.html`. You can customize the look and feel by editing this file.

## 6. Security Considerations

- **CORS**: Currently configured to allow all origins (`*`). Update `app.py` to restrict this to your production domain.
- **Authentication**: The `ProductionUserResolver` uses a simple cookie-based approach. For real-world production, consider integrating with an OIDC provider (like Google, GitHub, or Auth0) and validating JWT tokens.
- **Database Access**: Ensure the database user has minimal required permissions (e.g., read-only for data analysis).
