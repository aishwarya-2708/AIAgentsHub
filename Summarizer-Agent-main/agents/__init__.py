from .extractive_agent import ExtractiveAgent
from .abstractive_agent import AbstractiveAgent
from .bullet_agent import BulletAgent
from .tldr_agent import TLDRAgent
from .detailed_agent import DetailedAgent

class AgentRegistry:
    """Manages all available multimodal agents"""

    def __init__(self):
        self.agents = {}
        self.register_default_agents()

    def register_default_agents(self):
        """Register all default agents"""
        self.register_agent(ExtractiveAgent())
        self.register_agent(AbstractiveAgent())
        self.register_agent(BulletAgent())
        self.register_agent(TLDRAgent())
        self.register_agent(DetailedAgent())

    def register_agent(self, agent):
        """Register a new agent"""
        self.agents[agent.agent_id] = agent

    def get_agent(self, agent_id):
        """Get agent by ID"""
        return self.agents.get(agent_id)

    def get_all_agents(self):
        """Get all registered agents"""
        return list(self.agents.values())

    def run_agent(self, agent_id, text, video_path=None, images=None):
        """Run a specific agent with multimodal input"""
        agent = self.get_agent(agent_id)
        if not agent:
            return f"Error: Agent {agent_id} not found"
        return agent.generate_summary(text_data=text, video_path=video_path, images=images)

    def run_all_agents(self, text, video_path=None, images=None):
        """Run all agents in parallel (simplified)"""
        results = []
        for agent in self.get_all_agents():
            summary = agent.generate_summary(text_data=text, video_path=video_path, images=images)
            results.append({
                "agent_id": agent.agent_id,
                "agent_name": agent.name,
                "summary": summary,
                "agent_info": agent.get_info()
            })
        return results

# Create a global instance
agent_registry = AgentRegistry()