from .base_agent import BaseAgent

class BulletAgent(BaseAgent):
    """Creates bullet point summaries"""

    def __init__(self):
        super().__init__(agent_id=3, name="📋 Bullet Points Agent")
        self.agent_icon = "📋"
        self.description = "Creates structured, scannable bullet point summaries from all media types"

    def get_system_prompt(self) -> str:
        return """You are an expert at creating structured, scannable summaries from multimodal content.
        Extract key information from text, video descriptions, and image information
        and present it as clear, concise bullet points.
        Focus on main ideas, important details, and actionable information across all media types."""

    def get_instruction(self) -> str:
        return """Extract the key information from the provided multimodal content and
        present it as 4-6 bullet points. Each bullet should start with • and cover a
        distinct main idea or important detail from any of the media sources.

        Format:
        • [First key point]
        • [Second key point]
        • [Third key point]"""

    def get_temperature(self) -> float:
        return 0.5  # Moderate temperature for structured output

    def get_info(self) -> dict:
        info = super().get_info()
        info["description"] = self.description
        info["strength"] = "Structured output, easy to scan"
        info["best_for"] = ["Meeting notes", "Research papers", "Product descriptions"]
        return info