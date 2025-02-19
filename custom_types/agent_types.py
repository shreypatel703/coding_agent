from typing import TypedDict, List, Optional, Union
from .base_types import (
    GitHubFile, 
    TestProposal, 
    CodeReview,
    TestGatingDecision
)

class AgentContext(TypedDict):
    repository: str
    pull_number: int
    head_ref: str
    files: List[GitHubFile]
    commit_messages: List[str]

class AgentResponse(TypedDict):
    success: bool
    data: Union[TestProposal, CodeReview, TestGatingDecision]
    errors: Optional[List[str]] 