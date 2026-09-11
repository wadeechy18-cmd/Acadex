from pydantic import BaseModel

import anthropic

from app.ai.provider import AIGenerationResult, AIProvider


class AnthropicProvider(AIProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def generate_structured(self, *, system: str, prompt: str, schema: type[BaseModel]) -> AIGenerationResult:
        response = self._client.messages.parse(
            model=self._model,
            max_tokens=8000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_format=schema,
        )
        return AIGenerationResult(
            parsed=response.parsed_output,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=self._model,
        )
