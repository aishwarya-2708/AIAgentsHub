from .base_agent import BaseAgent

class TLDRAgent(BaseAgent):
    """Creates extremely concise summaries"""

    def __init__(self):
        super().__init__(agent_id=4, name="⚡ TL;DR Agent")
        self.agent_icon = "⚡"
        self.description = "Creates extremely concise summaries that capture the absolute essence in minimal words"

    def get_system_prompt(self) -> str:
        return """You are a TL;DR (Too Long; Didn't Read) summarization expert for multimodal content.
        Your task is to create extremely concise summaries that capture the absolute essence
        from text, video, and images in minimal words. Be direct, avoid fluff, and get straight to the point."""

    def get_instruction(self) -> str:
        return """Provide a TL;DR summary of the following multimodal content.
        Maximum 1-2 sentences or one short paragraph.
        Capture only the most essential information from all media sources.
        Be brutally concise.

        TL;DR:"""

    def get_temperature(self) -> float:
        return 0.6  # Slightly creative but concise

    def generate_summary(self, text_data=None, video_path=None, images=None, max_tokens=120) -> str:
        """Override for shorter TL;DR summaries"""
        return super().generate_summary(text_data, video_path, images, max_tokens)

    def get_info(self) -> dict:
        info = super().get_info()
        info["description"] = self.description
        info["strength"] = "Extreme conciseness, quick overview"
        info["best_for"] = ["Social media", "Quick updates", "Executive summaries"]
        return info