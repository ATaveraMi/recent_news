""" A2A Server -> FastAPI + WebSockets

Provides HTTP/WebSocket endpoints for agent communication
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Set
import asyncio
from agents.protocol import A2AProtocol, A2AMessage, AgentInfo
import json
import logging
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
            