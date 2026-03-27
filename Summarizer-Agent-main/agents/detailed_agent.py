from .base_agent import BaseAgent

class DetailedAgent(BaseAgent):
    """Creates comprehensive, detailed summaries"""

    def __init__(self):
        super().__init__(agent_id=5, name="📚 Detailed Agent")
        self.agent_icon = "📚"
        self.description = "Creates comprehensive summaries covering all important aspects from all media types"

    def get_system_prompt(self) -> str:
        return """You are a comprehensive summarization agent for multimodal content.
        Your task is to create detailed summaries that cover all important aspects
        of text, video content, and images. Include main ideas, supporting details,
        context, and implications where relevant across all media types."""

    def get_instruction(self) -> str:
        return """Create a comprehensive summary of the following multimodal content.
        Cover all key points, important details, and context from all available media sources.
        Aim for 4-6 sentences that provide a complete overview.

        Comprehensive Summary:"""

    def get_temperature(self) -> float:
        return 0.8  # Higher temperature for more detailed generation

    def generate_summary(self, text_data=None, video_path=None, images=None, max_tokens=250) -> str:
        """Override to allow more tokens for detailed summary"""
        return super().generate_summary(text_data, video_path, images, max_tokens)

    def get_info(self) -> dict:
        info = super().get_info()
        info["description"] = self.description
        info["strength"] = "Comprehensive coverage, detailed analysis"
        info["best_for"] = ["Research reports", "Legal briefs", "Technical documentation"]
        return info