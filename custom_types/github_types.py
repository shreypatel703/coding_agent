from typing import TypedDict, List, Optional, Literal, Dict
from .base_types import GitHubFile, GitHubCommit, PullRequestInfo

class Repository(TypedDict):
    name: str
    owner: str
    default_branch: str
    private: bool

class Label(TypedDict):
    name: str
    color: str
    description: Optional[str]

class WebhookEvent(TypedDict):
    event_type: str
    action: str
    repository: Repository
    sender: Dict[str, str]
    pull_request: Optional[PullRequestInfo]
    label: Optional[Label] 