""" A2A Protocol

Defines the A2A protocol for agent communication
"""

"""
A2A (Agent-to-Agent) Protocol Implementation
Enables agents to communicate and coordinate with each other
"""
from typing import Dict, Any, Optional, List, Callable
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import asyncio
import uuid
import logging
logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Types of A2A messages"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


class AgentCapability(str, Enum):
    """Agent capabilities"""
    DATA_RETRIEVAL = "data_retrieval"
    DATA_ANALYSIS = "data_analysis"
    TASK_EXECUTION = "task_execution"
    REASONING = "reasoning"


class A2AMessage(BaseModel):
    """Agent-to-Agent message format"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType
    sender_id: str
    receiver_id: Optional[str] = None  # None for broadcast
    timestamp: datetime = Field(default_factory=datetime.now)
    payload: Dict[str, Any]
    in_reply_to: Optional[str] = None


class AgentInfo(BaseModel):
    """Information about an agent"""
    agent_id: str
    name: str
    capabilities: List[AgentCapability]
    endpoint: str
    status: str = "active"


class A2AProtocol:
    """Handles Agent-to-Agent communication"""

    def __init__(self, agent_id: str, agent_name: str, capabilities: List[AgentCapability]):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.capabilities = capabilities
        self.known_agents: Dict[str, AgentInfo] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.pending_responses: Dict[str, asyncio.Future] = {}

    def register_handler(self, action: str, handler: Callable):
        """Register a message handler for a specific action"""
        self.message_handlers[action] = handler
        logger.info(f"Registered handler for action: {action}")

    async def send_message(
        self,
        receiver_id: str,
        message_type: MessageType,
        payload: Dict[str, Any],
        in_reply_to: Optional[str] = None
    ) -> A2AMessage:
        """Send a message to another agent"""
        message = A2AMessage(
            message_type=message_type,
            sender_id=self.agent_id,
            receiver_id=receiver_id,
            payload=payload,
            in_reply_to=in_reply_to
        )

        logger.info(
            f"Sending {message_type} message to {receiver_id}: "
            f"{payload.get('action', 'unknown')}"
        )

        return message

    async def handle_message(self, message: A2AMessage) -> Optional[A2AMessage]:
        """Handle an incoming message"""
        logger.info(
            f"Received {message.message_type} from {message.sender_id}: "
            f"{message.payload.get('action', 'unknown')}"
        )

        # If it's a response to a pending request, resolve the future
        if message.in_reply_to and message.in_reply_to in self.pending_responses:
            future = self.pending_responses.pop(message.in_reply_to)
            future.set_result(message)
            return None

        # Handle based on message type
        if message.message_type == MessageType.REQUEST:
            action = message.payload.get("action")
            if action in self.message_handlers:
                try:
                    result = await self.message_handlers[action](message.payload)
                    return await self.send_message(
                        receiver_id=message.sender_id,
                        message_type=MessageType.RESPONSE,
                        payload={"result": result, "success": True},
                        in_reply_to=message.message_id
                    )
                except Exception as e:
                    logger.error(f"Error handling action {action}: {e}")
                    return await self.send_message(
                        receiver_id=message.sender_id,
                        message_type=MessageType.ERROR,
                        payload={"error": str(e), "success": False},
                        in_reply_to=message.message_id
                    )
            else:
                logger.warning(f"No handler for action: {action}")
                return await self.send_message(
                    receiver_id=message.sender_id,
                    message_type=MessageType.ERROR,
                    payload={"error": f"Unknown action: {action}", "success": False},
                    in_reply_to=message.message_id
                )

        return None

    async def request_and_wait(
        self,
        receiver_id: str,
        action: str,
        params: Dict[str, Any],
        timeout: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """Send a request and wait for response"""
        message = await self.send_message(
            receiver_id=receiver_id,
            message_type=MessageType.REQUEST,
            payload={"action": action, "params": params}
        )

        # Create a future for the response
        future = asyncio.Future()
        self.pending_responses[message.message_id] = future

        try:
            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=timeout)
            return response.payload
        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for response from {receiver_id}")
            self.pending_responses.pop(message.message_id, None)
            return None

    def register_agent(self, agent_info: AgentInfo):
        """Register another agent in the network"""
        self.known_agents[agent_info.agent_id] = agent_info
        logger.info(f"Registered agent: {agent_info.name} ({agent_info.agent_id})")

    def get_agents_by_capability(self, capability: AgentCapability) -> List[AgentInfo]:
        """Find agents with a specific capability"""
        return [
            agent for agent in self.known_agents.values()
            if capability in agent.capabilities
        ]

    def get_agent_info(self) -> AgentInfo:
        """Get this agent's information"""
        return AgentInfo(
            agent_id=self.agent_id,
            name=self.agent_name,
            capabilities=self.capabilities,
            endpoint=f"agent://{self.agent_id}"
        )