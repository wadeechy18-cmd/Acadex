"""AI provider abstraction. No code outside this package (and the one
concrete provider module) should import a vendor SDK directly -- swapping
providers is a config change (ai_provider setting + credentials), never a
code change to any caller. See docs/LESSON_PLANNER_ARCHITECTURE.md section
10. Mirrors app/storage/base.py's StorageBackend pattern deliberately.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from pydantic import BaseModel


@dataclass
class AIGenerationResult:
    parsed: BaseModel
    input_tokens: int
    output_tokens: int
    model: str


class AIProvider(ABC):
    @abstractmethod
    def generate_structured(self, *, system: str, prompt: str, schema: type[BaseModel]) -> AIGenerationResult:
        """One call in, one schema-validated object out. Implementations must
        never make more than one underlying model call per invocation -- the
        brief is explicit that one structured request beats ten for the same
        lesson plan. Callers are responsible for recording usage.
        """


def get_ai_provider() -> AIProvider | None:
    """FastAPI dependency. Returns None when no API key is configured --
    callers respond 503, the app itself never fails to start over this.
    """
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.anthropic_api_key:
        return None

    from app.ai.anthropic_provider import AnthropicProvider

    return AnthropicProvider(api_key=settings.anthropic_api_key, model=settings.ai_model)
