from .base_agent import BaseAgent

class ExtractiveAgent(BaseAgent):
    """Extracts key sentences verbatim from text"""

    def __init__(self):
        super().__init__(agent_id=1, name="📄 Extractive Agent")
        self.agent_icon = "📄"
        self.description = "Extracts the most important sentences verbatim from text, video transcripts, or image descriptions"

    def get_system_prompt(self) -> str:
        return """You are an expert extractive summarization agent for multimodal content.
        Your task is to extract the most important information VERBATIM from the provided content.
        For multimodal content, focus on extracting key textual descriptions, important facts,
        and significant details without modification."""

    def get_instruction(self) -> str:
        return """Extract exactly 3-4 most important pieces of information from the provided content verbatim.
        Do not modify the original wording. Do not add commentary.
        Just list the extracted information in order:
        1. [First important point]
        2. [Second important point]
        3. [Third important point]
        4. [Fourth important point]"""

    def get_temperature(self) -> float:
        return 0.3  # Low temperature for verbatim extraction

    def get_info(self) -> dict:
        info = super().get_info()
        info["description"] = self.description
        info["strength"] = "Preserves original wording, good for factual content"
        info["best_for"] = ["Legal documents", "Technical specifications", "Factual reports"]
        return info