import requests
import base64
import json
from abc import ABC, abstractmethod
from PIL import Image
import io
import os
from pathlib import Path

class BaseAgent(ABC):
    """Base class for all multimodal summarization agents"""

    def __init__(self, agent_id: int, name: str,
                 ollama_url="http://localhost:11435/api/generate",
                 model="llama3.2:latest"):
        self.agent_id = agent_id
        self.name = name
        self.ollama_url = ollama_url
        self.model = model
        self.agent_icon = "🤖"  # Default icon

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return agent-specific system prompt"""
        pass

    @abstractmethod
    def get_instruction(self) -> str:
        """Return agent-specific instruction"""
        pass

    def preprocess_media(self, text_data=None, video_path=None, images=None):
        """Preprocess multimodal inputs for the model"""
        media_context = []

        # Handle text
        if text_data and text_data.strip():
            media_context.append(f"TEXT CONTENT:\n{text_data}")

        # Handle video
        if video_path and os.path.exists(video_path):
            try:
                # Get video info
                import cv2
                cap = cv2.VideoCapture(video_path)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                duration = frame_count / fps if fps > 0 else 0
                cap.release()

                video_info = f"VIDEO FILE:\n- Duration: {duration:.1f} seconds\n- Frames: {frame_count}\n- FPS: {fps:.1f}"
                media_context.append(video_info)
            except Exception as e:
                media_context.append(f"VIDEO INFO: [Video file available but analysis failed: {str(e)}]")

        # Handle images
        if images:
            if isinstance(images, str):
                images = [images]

            image_info = f"IMAGES: {len(images)} image(s) provided"
            media_context.append(image_info)

            # Add descriptions of first few images
            for i, img_path in enumerate(images[:2]):  # Limit to 2 images
                if os.path.exists(img_path):
                    try:
                        img = Image.open(img_path)
                        img_info = f"Image {i+1}: {img.size[0]}x{img.size[1]} pixels, {img.mode} format"
                        media_context.append(img_info)
                        img.close()
                    except Exception as e:
                        media_context.append(f"Image {i+1}: [Could not read image details]")

        return "\n\n".join(media_context)

    def generate_summary(self, text_data=None, video_path=None, images=None, max_tokens=200) -> str:
        """Generate summary from multimodal inputs"""

        # Preprocess all media inputs
        media_context = self.preprocess_media(text_data, video_path, images)

        if not media_context.strip():
            return "No content provided for summarization"

        # Build the complete prompt
        system_prompt = self.get_system_prompt()
        instruction = self.get_instruction()

        # Create context-aware prompt
        if video_path or images:
            prompt = f"""{instruction}

Multimodal Content:
{media_context}

Please provide a summary that integrates information from all available media types:"""
        else:
            prompt = f"""{instruction}

Content:
{media_context}

Summary:"""

        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": self.get_temperature(),
                    "top_p": 0.9,
                    "stop": ["###", "END", "Summary:"]
                }
            }

            if system_prompt:
                payload["system"] = system_prompt

            response = requests.post(self.ollama_url, json=payload, timeout=120)
            response.raise_for_status()
            result = response.json().get("response", "").strip()

            # Clean up result
            result = result.replace("Summary:", "").replace("TL;DR:", "").replace("Key points:", "").strip()
            return result

        except requests.exceptions.Timeout:
            return "Error: Request timeout - the model took too long to respond"
        except requests.exceptions.ConnectionError:
            return "Error: Cannot connect to Ollama server. Make sure Ollama is running."
        except Exception as e:
            return f"Error: {str(e)}"

    def get_temperature(self) -> float:
        """Get temperature parameter for generation"""
        return 0.7

    def get_info(self) -> dict:
        """Get agent information"""
        return {
            "id": self.agent_id,
            "name": self.name,
            "icon": self.agent_icon,
            "type": self.__class__.__name__,
            "modalities": ["text", "images", "video"]
        }