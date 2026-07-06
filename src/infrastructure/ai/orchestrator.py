import base64
from typing import List, Optional, Dict, Any
from src.config import settings
from src.application.interfaces.ai_orchestrator import LLMAdapter
from src.infrastructure.ai.adapters.gemini import GeminiAdapter
from src.infrastructure.ai.adapters.openai import OpenAIAdapter
from src.infrastructure.ai.adapters.claude import ClaudeAdapter
from src.infrastructure.ai.adapters.ollama import OllamaAdapter
from src.infrastructure.logging import get_logger

logger = get_logger("AI")

class AIOrchestrator:
    def __init__(self) -> None:
        self.adapters: Dict[str, LLMAdapter] = {}
        self._init_adapters()

    def _init_adapters(self) -> None:
        # Initialize Gemini adapter
        if settings.gemini_api_key and settings.gemini_api_key != "your_gemini_key_here":
            self.adapters["gemini"] = GeminiAdapter(
                api_key=settings.gemini_api_key,
                model_name=settings.llm.gemini.model,
                temperature=settings.llm.temperature,
            )
        
        # Initialize OpenAI adapter
        if settings.openai_api_key and settings.openai_api_key != "your_openai_key_here":
            self.adapters["openai"] = OpenAIAdapter(
                api_key=settings.openai_api_key,
                model_name=settings.llm.openai.model,
                temperature=settings.llm.temperature,
            )

        # Initialize Claude adapter
        if settings.claude_api_key and settings.claude_api_key != "your_claude_key_here":
            self.adapters["claude"] = ClaudeAdapter(
                api_key=settings.claude_api_key,
                model_name=settings.llm.claude.model,
                temperature=settings.llm.temperature,
            )

        # Initialize OpenRouter adapter (leveraging OpenAIAdapter structure)
        if settings.openrouter_api_key and settings.openrouter_api_key != "your_openrouter_key_here":
            self.adapters["openrouter"] = OpenAIAdapter(
                api_key=settings.openrouter_api_key,
                model_name=settings.llm.openai.model,
                temperature=settings.llm.temperature,
                base_url="https://openrouter.ai/api/v1",
            )

        # Initialize local Ollama adapter
        if settings.llm.ollama.url:
            self.adapters["ollama"] = OllamaAdapter(
                base_url=settings.llm.ollama.url,
                model_name=settings.llm.ollama.model,
            )

    def get_adapter(self, provider: Optional[str] = None) -> LLMAdapter:
        prov = provider or settings.llm.active_provider
        if prov in self.adapters:
            return self.adapters[prov]
        
        # Fallback to any available adapter if requested is missing
        if self.adapters:
            first_available = list(self.adapters.keys())[0]
            logger.warning(
                "Active provider not configured, choosing fallback adapter",
                requested=prov,
                selected=first_available,
            )
            return self.adapters[first_available]
        
        raise RuntimeError("No LLM adapters configured. Check your env variables and config.yaml.")

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        provider: Optional[str] = None,
    ) -> str:
        prov = provider or settings.llm.active_provider
        adapter = self.get_adapter(prov)
        try:
            return await adapter.generate_text(prompt, system_instruction, temperature)
        except Exception as e:
            logger.warning("Primary text generation failed, trying fallbacks...", provider=prov, error=str(e))
            for name, other_adapter in self.adapters.items():
                if name != prov:
                    try:
                        logger.info("Attempting fallback text generation", fallback_provider=name)
                        return await other_adapter.generate_text(prompt, system_instruction, temperature)
                    except Exception:
                        continue
            raise

    async def get_embeddings(self, text: str, provider: Optional[str] = None) -> List[float]:
        prov = provider or settings.llm.active_provider
        try:
            adapter = self.get_adapter(prov)
            return await adapter.get_embeddings(text)
        except (NotImplementedError, Exception) as e:
            logger.info("Embedding generation failed on primary, trying fallbacks...", provider=prov, error=str(e))
            for name, other_adapter in self.adapters.items():
                if name != prov:
                    try:
                        return await other_adapter.get_embeddings(text)
                    except (NotImplementedError, Exception):
                        continue
            raise RuntimeError("No configured LLM adapter was able to generate embeddings.")

    async def analyze_image(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
        provider: Optional[str] = None,
    ) -> str:
        prov = provider or settings.llm.active_provider
        adapter = self.get_adapter(prov)
        try:
            return await adapter.analyze_image(image_bytes, mime_type, prompt)
        except Exception as e:
            logger.warning("Primary image analysis failed, trying fallbacks...", provider=prov, error=str(e))
            for name, other_adapter in self.adapters.items():
                if name != prov:
                    try:
                        return await other_adapter.analyze_image(image_bytes, mime_type, prompt)
                    except Exception:
                        continue
            raise

    async def generate_image(self, prompt: str, provider: Optional[str] = None) -> bytes:
        prov = provider or settings.llm.active_provider
        try:
            adapter = self.get_adapter(prov)
            return await adapter.generate_image(prompt)
        except (NotImplementedError, Exception) as e:
            logger.info("Image generation failed on primary, trying fallbacks...", provider=prov, error=str(e))
            for name, other_adapter in self.adapters.items():
                if name != prov:
                    try:
                        return await other_adapter.generate_image(prompt)
                    except (NotImplementedError, Exception):
                        continue
            raise RuntimeError("No configured LLM adapter was able to generate images.")

    async def double_pass_rewrite(self, raw_text: str) -> str:
        """
        Extract raw dry facts, then rewrite as a high-quality Telegram post.
        """
        # Step 1: Extract facts
        step1_system = (
            "You are an expert fact extractor. Your job is to extract only raw, dry, verifiable facts "
            "from the input text. Remove all opinions, marketing words, hype, clickbait, speculation, "
            "and AI jargon. Format facts as a clean bulleted list. Do not write a narrative."
        )
        logger.info("Starting double-pass rewrite: Step 1 (Fact Extraction)")
        facts = await self.generate_text(prompt=raw_text, system_instruction=step1_system)
        logger.debug("Extracted facts", facts=facts)

        # Step 2: Write final post
        step2_system = (
            "You are a professional, high-end copywriter and tech journalist. "
            "Write a single, polished Telegram post based ONLY on the provided bulleted list of facts. "
            "Guidelines:\n"
            "- Style: Modern, engaging, concise, and highly readable.\n"
            "- Tone: Professional, direct, completely devoid of AI fluff, exaggeration, or corporate speak.\n"
            "- Formatting: Use paragraphs, bold text for key details, and minimal clean bullet points if needed. Do not use generic emojis or hashtags unless highly relevant.\n"
            "- Avoid any speculative statements or facts not present in the input list."
        )
        logger.info("Starting double-pass rewrite: Step 2 (Styled Rewrite)")
        rewritten_text = await self.generate_text(prompt=facts, system_instruction=step2_system)
        logger.debug("Final rewritten post", post=rewritten_text)
        return rewritten_text
