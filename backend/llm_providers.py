# ============================================
# ShieldCV — LLM Providers
# Abstraction for NVIDIA NIM (Nemotron), OpenAI, and Google Gemini
# ============================================

import json
import os
from abc import ABC, abstractmethod


def load_env_file():
    """Load key-value pairs from .env in backend directory into os.environ."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    os.environ[k] = v


# Automatically load .env on import
load_env_file()


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(self, system_prompt: str, user_prompt: str, json_mode: bool = False, max_tokens: int = 1024) -> str:
        """Generate a response from the LLM."""
        pass

    @abstractmethod
    def name(self) -> str:
        pass


class NvidiaNimProvider(LLMProvider):
    """
    NVIDIA NIM / Build provider.
    Runs frontier models like Nemotron-3 Ultra 550B via OpenAI-compatible endpoints.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        from openai import AsyncOpenAI
        load_env_file()
        key = api_key or os.getenv("NVIDIA_API_KEY") or os.getenv("NVDIA_API_KEY")
        self.model = model or os.getenv("NVIDIA_MODEL") or "nvidia/nemotron-3-ultra-550b-a55b"
        self.client = AsyncOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=key,
            timeout=25.0
        )

    async def generate(self, system_prompt: str, user_prompt: str, json_mode: bool = False, max_tokens: int = 1024) -> str:
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.0,  # Deterministic for consistent extraction
            "max_tokens": max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        return content.strip()

    def name(self) -> str:
        return f"NVIDIA NIM ({self.model})"


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider (GPT-4o, GPT-4o-mini, etc.)"""

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini"):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model

    async def generate(self, system_prompt: str, user_prompt: str, json_mode: bool = False, max_tokens: int = 1024) -> str:
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.0,
            "max_tokens": max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    def name(self) -> str:
        return f"OpenAI ({self.model})"


class GeminiProvider(LLMProvider):
    """Google Gemini provider."""

    def __init__(self, api_key: str | None = None, model: str = "gemini-2.0-flash"):
        import google.generativeai as genai
        genai.configure(api_key=api_key or os.getenv("GOOGLE_API_KEY"))
        self.model_name = model
        self.genai = genai

    async def generate(self, system_prompt: str, user_prompt: str, json_mode: bool = False, max_tokens: int = 1024) -> str:
        generation_config = {
            "temperature": 0.0,
            "max_output_tokens": max_tokens,
        }

        if json_mode:
            generation_config["response_mime_type"] = "application/json"

        model = self.genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_prompt,
            generation_config=generation_config,
        )

        response = await model.generate_content_async(user_prompt)
        return response.text

    def name(self) -> str:
        return f"Gemini ({self.model_name})"


def get_provider(provider_name: str = "auto", api_key: str | None = None) -> LLMProvider:
    """
    Get an LLM provider. Tries to auto-detect based on available API keys.

    Args:
        provider_name: "nvidia", "openai", "gemini", or "auto" (detect from env)
        api_key: Optional explicit API key
    """
    # Reload env in case of updates
    load_env_file()

    nvidia_key = os.getenv("NVIDIA_API_KEY") or os.getenv("NVDIA_API_KEY")

    if provider_name == "auto":
        if api_key:
            if api_key.startswith("nvapi-"):
                return NvidiaNimProvider(api_key=api_key)
            elif api_key.startswith("sk-"):
                return OpenAIProvider(api_key=api_key)
            else:
                return GeminiProvider(api_key=api_key)

        # Check environment variables
        if nvidia_key:
            return NvidiaNimProvider()
        elif os.getenv("OPENAI_API_KEY"):
            return OpenAIProvider()
        elif os.getenv("GOOGLE_API_KEY"):
            return GeminiProvider()
        else:
            raise ValueError(
                "No API key found. Set NVIDIA_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY."
            )

    elif provider_name == "nvidia":
        return NvidiaNimProvider(api_key=api_key)
    elif provider_name == "openai":
        return OpenAIProvider(api_key=api_key)
    elif provider_name == "gemini":
        return GeminiProvider(api_key=api_key)
    else:
        raise ValueError(f"Unknown provider: {provider_name}. Use 'nvidia', 'openai', or 'gemini'.")
