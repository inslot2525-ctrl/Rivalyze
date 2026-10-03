"""Thin Gemini wrapper: schema-constrained JSON out, with a fallback chain of models."""
from typing import Type, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from config import settings

T = TypeVar("T", bound=BaseModel)


class LLMUnavailable(Exception):
    pass


class LLM:
    def __init__(self):
        if not settings.gemini_api_key:
            raise LLMUnavailable("GEMINI_API_KEY is not set")
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.calls = 0

    async def structured(self, system: str, prompt: str, schema: Type[T], temperature: float = 0.3,
                         fast: bool = False) -> T:
        """Ask for JSON matching `schema`, falling through the configured models on failure.

        `fast` starts from the lightest model: right for routing steps, wrong for the analysis.
        """
        config = types.GenerateContentConfig(
            system_instruction=system, temperature=temperature,
            response_mime_type="application/json", response_schema=schema,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
        last_error: Exception = LLMUnavailable("no model tried")
        models = [m.strip() for m in settings.gemini_models.split(",") if m.strip()]
        for model in (models[::-1] if fast else models):
            try:
                self.calls += 1
                resp = await self.client.aio.models.generate_content(
                    model=model, contents=prompt, config=config)
                return schema.model_validate_json(resp.text or "")
            except Exception as e:  # quota, overload or malformed JSON: try the next model
                last_error = e
        raise LLMUnavailable(f"Gemini request failed: {str(last_error)[:300]}")
