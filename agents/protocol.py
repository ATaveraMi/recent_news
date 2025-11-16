""" A2A Protocol

Defines the A2A protocol for agent communication
"""

class A2AProtocol:
    """A2A Protocol"""
    def __init__(self, agent_name: str):
        self.agent_name = agent_name

    def __str__(self):
        return f"A2AProtocol(agent_name={self.agent_name})"