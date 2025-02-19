# Standard library imports
from typing import List, Dict, Tuple, Any
from github.Repository import Repository
from github.IssueComment import IssueComment

# Local imports
from utils import github_utils
from utils.file_utils import get_github_file
from utils.logging_utils import log_info, log_error, log_debug
from prompts.fix_test_prompt import generate_fix_response
from custom_types.base_types import GitHubFile, GitHubCommit, CodeReview, TestGatingDecision
from custom_types.agent_types import AgentContext, AgentResponse


class PRBaseAgent:
    """Base class for pull request agents that handle PR events"""
    def __init__(self):
        pass

    def handle_pull_request(self, repository: Repository, pull_number: int, head_ref: str) -> Tuple[List[GitHubFile], List[GitHubCommit]]:
        """
        Fetches files and commits for a pull request
        
        Args:
            repository: The GitHub repository object
            pull_number: The PR number
            head_ref: The head branch reference
            
        Returns:
            Tuple of (files, commits)
        """
        log_info(f"Fetching files and commits for PR #{pull_number}")
        files = [get_github_file(f, repository, head_ref) for f in github_utils.get_pull_request_files(repository, pull_number)]
        files = [f for f in files if not f.excluded]
        commits = [GitHubCommit(sha=commit.sha, message=commit.commit.message) for commit in github_utils.get_pull_request_commits(repository, pull_number)]
        return files, commits