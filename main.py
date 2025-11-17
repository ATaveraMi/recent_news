""" A2A Server -> FastAPI + WebSockets

Provides HTTP/WebSocket endpoints for agent communication
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict
from agents.protocols.protocol import A2AProtocol, A2AMessage, AgentCapability
import json
import logging
from dotenv import load_dotenv
from agents.orchestrator import Orchestrator
from agents.data_agent import DataAgent
from agents.llm_analysis_agent import LLMAnalysisAgent
from os import getenv
logger = logging.getLogger(__name__)

class A2AServer:
    """Server for A2A protocol"""
    def __init__(self, protocol: A2AProtocol, host: str = "0.0.0.0", port: int = 8000):
        self.protocol = protocol
        self.host = host
        self.port = port
        self.app = FastAPI(title=f"Reportero - {protocol.agent_name}")
         # WebSocket connections
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_agents: Dict[str, str] = {}  # websocket -> agent_id
        self._setup_routes()
        
    def _setup_routes(self):
        """Setup routes for the server"""
        @self.app.get("/")
        async def root():
            return {"message": "Welcome to the A2A Server"}
        
        @self.app.get("/info")
        async def info():
            return self.protocol.get_agent_info().to_dict()
        
        @self.app.post("/message")
        async def receive_message(message_dict: dict):
            """Receive a message via HTTP"""
            try:
                message = A2AMessage(**message_dict)

                # Handle the message
                response = await self.protocol.handle_message(message)

                if response:
                    return response.dict()
                else:
                    return {"status": "processed"}
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                raise HTTPException(status_code=400, detail=str(e))
            
        @self.app.websocket("/ws/{agent_id}")
        async def websocket_endpoint(websocket: WebSocket, agent_id: str):
            """WebSocket endpoint for real-time communication"""
            await websocket.accept()
            self.active_connections[agent_id] = websocket
            self.connection_agents[id(websocket)] = agent_id

            logger.info(f"Agent {agent_id} connected via WebSocket")

            try:
                while True:
                    # Receive message
                    data = await websocket.receive_text()
                    message_dict = json.loads(data)
                    message = A2AMessage(**message_dict)

                    # Handle message
                    response = await self.protocol.handle_message(message)

                    # Send response if any
                    if response:
                        await websocket.send_text(response.json())

            except WebSocketDisconnect:
                logger.info(f"Agent {agent_id} disconnected")
                self.active_connections.pop(agent_id, None)
                self.connection_agents.pop(id(websocket), None)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                self.active_connections.pop(agent_id, None)
                self.connection_agents.pop(id(websocket), None)
            @self.app.get("/agents")
            async def list_agents():
                """List known agents"""
                return {
                    "agents": [
                        agent.dict() for agent in self.protocol.known_agents.values()
                    ]
                }
    async def send_to_agent(self, agent_id: str, message: A2AMessage):
        """Send message to a specific agent via WebSocket"""
        if agent_id in self.active_connections:
            websocket = self.active_connections[agent_id]
            try:
                await websocket.send_text(message.json())
                logger.info(f"Sent message to {agent_id} via WebSocket")
            except Exception as e:
                logger.error(f"Failed to send via WebSocket: {e}")
        else:
            logger.warning(f"Agent {agent_id} not connected via WebSocket")

    def run(self):
        """Run the server"""
        import uvicorn
        logger.info(f"Starting A2A server on {self.host}:{self.port}")
        uvicorn.run(self.app, host=self.host, port=self.port)

    async def start(self):
        """Start server asynchronously"""
        import uvicorn
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()

# ----- Entrypoint / ASGI app exposure -----
logging.basicConfig(level=logging.INFO)
load_dotenv()

# Wire up agents and orchestrator
_api_key = getenv("OPENAI_API_KEY")
if not _api_key:
    raise RuntimeError("OPENAI_API_KEY must be set to run LLM-based analysis.")
_orchestrator = Orchestrator(
    data_agent=DataAgent(),
    analysis_agent=LLMAnalysisAgent(model_name="gpt-4o-mini"),
)

_protocol = A2AProtocol(
    agent_id="reportero",
    agent_name="Reportero",
    capabilities=[AgentCapability.DATA_RETRIEVAL, AgentCapability.DATA_ANALYSIS],
)
_server = A2AServer(_protocol, host="127.0.0.1", port=8000)

# Expose FastAPI app for uvicorn (e.g., `uv run uvicorn main:app --reload`)
app = _server.app

# Register handler for workflow.news
async def handle_workflow_news(payload: dict) -> Dict:
    params = payload.get("params") or {}
    query = params.get("query") or params.get("topic") or "recent news"
    email_to = params.get("email_to")
    return await _orchestrator.run_workflow(query=query, email_to=email_to)

_protocol.register_handler("workflow.news", handle_workflow_news)

if __name__ == "__main__":
    _server.run()