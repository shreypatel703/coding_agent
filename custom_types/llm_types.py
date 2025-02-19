from typing import TypedDict, List, Optional, Any, Dict
from .base_types import LLMConfig

class PromptTemplate(TypedDict):
    template: str
    input_variables: List[str]

class LLMTask(TypedDict):
    name: str
    prompt_template: PromptTemplate
    input_model: Any
    output_model: Any

class LLMHandler(TypedDict):
    config: LLMConfig
    tasks: Dict[str, LLMTask] 