from typing import TypedDict, List, Dict, Optional, Union, Literal
from datetime import datetime
from dataclasses import dataclass

# GitHub Related Types
@dataclass
class GitHubFile:
    filename: str
    patch: Optional[str]
    status: str
    additions: int
    deletions: int
    excluded: bool
    content: Optional[str]

@dataclass
class GithubTestFile:
    filename: str
    content: Optional[str]

@dataclass
class GitHubCommit:
    message: str
    sha: str

class PullRequestInfo(TypedDict):
    number: int
    title: str
    body: Optional[str]
    state: Literal['open', 'closed']
    head_ref: str
    base_ref: str
    created_at: datetime
    updated_at: datetime

# LLM Related Types
@dataclass
class LLMConfig:
    model: str
    temperature: Optional[float]
    max_tokens: Optional[int]
    top_p: Optional[float]

@dataclass
class LLMResponse:
    content: str
    model: str
    usage: Dict[str, int]

# Test Related Types
@dataclass
class Action:
    action: Literal["create", "update", "rename"]
    oldFilename: Optional[str]
@dataclass
class TestProposal:
    filename: str
    testType: Literal['unit', 'integration']
    testContent: str
    actions: List[Action]

@dataclass
class TestProposals:
    test_proposals: List[TestProposal]

@dataclass
class TestGatingDecision:
    shouldGenerateTests: bool
    reasoning: str
    recommendations: List[str]

# Code Review Types
@dataclass
class FileAnalysis:
    file_path: str
    analysis: str

@dataclass
class CodeReview:
    summary: str
    file_analyses: List[FileAnalysis]
    suggestions: List[str]

# API Response Types
@dataclass
class APIResponse:
    success: bool
    message: str
    data: Optional[Dict]
    errors: Optional[List[str]] 

@dataclass
class TestResult:
    file_path: str
    passed: bool
    error_message: Optional[str] = None
    retry_count: int = 0
