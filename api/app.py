from fastapi import FastAPI
from vanna.servers.fastapi import VannaFastAPIServer
from api.vanna_calls import agent

# Initialize Vanna Server
vanna_server = VannaFastAPIServer(agent)

# Create FastAPI app
app = vanna_server.create_app()

# Add root endpoint for health check
@app.get("/")
def read_root():
    return {"status": "ok", "service": "Vanna AI Backend"}
