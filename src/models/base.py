from dataclasses import dataclass
from typing import Any, Dict, List, Protocol, TypedDict

ChatMessage = TypedDict("ChatMessage", {"role": str, "content": str})

@dataclass
class GenerationResult:
    raw_text: str
    metadata: Dict[str, Any]

class ModelHandler(Protocol):
    def generate(self, messages: List[ChatMessage], *, max_tokens: int = 256, temperature: float = 0.0) -> GenerationResult:
        ...