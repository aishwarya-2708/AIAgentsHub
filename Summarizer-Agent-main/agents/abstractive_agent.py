from .base_agent import BaseAgent

class AbstractiveAgent(BaseAgent):
    """Summarizes content in own words"""

    def __init__(self):
        super().__init__(agent_id=2, name="✨ Abstractive Agent")
        self.agent_icon = "✨"
        self.description = "Summarizes content in own words while preserving key information, meaning, and context"

    def get_system_prompt(self) -> str:
        return """You are an expert abstractive summarization agent for multimodal content.
        Your task is to understand and synthesize information from text, video descriptions,
        and image information, then rewrite it concisely in your own words.
        Preserve all key information, meaning, and context while creating a fluent, coherent summary."""

    def get_instruction(self) -> str:
        return """Synthesize and summarize the following multimodal content in your own words
        (2-3 sentences maximum). Integrate information from all available media types.
        Preserve the key information and main ideas while making it more compact and readable."""

    def get_temperature(self) -> float:
        return 0.7  # Medium temperature for creative rewriting

    def generate_summary(self, text_data=None, video_path=None, images=None, max_tokens=180) -> str:
        """Override to handle multimodal synthesis"""
        return super().generate_summary(text_data, video_path, images, max_tokens)

    def get_info(self) -> dict:
        info = super().get_info()
        info["description"] = self.description
        info["strength"] = "Creative synthesis, fluent writing"
        info["best_for"] = ["News articles", "Blog posts", "Educational content"]
        return info