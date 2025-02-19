import json
import base64
from typing import List, Optional
from github import Github
from github.Repository import Repository
from github.PullRequest import PullRequest
from github.File import File
from github.IssueComment import IssueComment
from auth.github_auth import generate_installation_token
import subprocess
from utils.logging_utils import log_info, log_error

# Initialize GitHub Client
installation_token = generate_installation_token()
g = Github(installation_token)

def get_repository(owner: str, repo_name: str) -> Repository:
    """Fetch the repository object."""
    return g.get_repo(f"{owner}/{repo_name}")

def get_pull_request(repository: Repository, pull_number: int) -> PullRequest:
    """Fetch the pull request object."""
    return repository.get_pull(pull_number)

def get_pull_request_files(repository: Repository, pull_number: int) -> List[File]:
    """Fetch the files modified in a PR."""
    return get_pull_request(repository, pull_number).get_files()

def get_pull_request_commits(repository: Repository, pull_number: int) -> List[str]:
    """Fetch the commit messages of a PR."""
    return get_pull_request(repository, pull_number).get_commits()

def post_comment(repository: Repository, pull_number: int, message: str) -> IssueComment:
    """Post a comment on a PR."""
    return repository.get_issue(pull_number).create_comment(message)

def update_comment(comment: IssueComment, message: str) -> None:
    """Update an existing comment."""
    comment.edit(message)

def get_file_content_by_filename(repository: Repository, filename: str, ref: str) -> Optional[str]:
    """Get the content of a file by filename."""
    file_content = repository.get_contents(filename, ref)
    
    # Check if content exists and is in base64 encoded string format
    if hasattr(file_content, "content") and isinstance(file_content.content, str):
        return base64.b64decode(file_content.content).decode("utf-8")
    
    return None

def getFileContent(repository: Repository, file: File, ref: str) -> Optional[str]:
    if file.status == "removed":
        return None
    
    return get_file_content_by_filename(repository, file.filename, ref)\

def create_file(repository: Repository, filename: str, comment: str, file_content: str, branch: str) -> None:
    """Create a new file in the repository."""
    repository.create_file(filename, comment, file_content, branch=branch)

def update_file(repository: Repository, filename: str, comment: str, file_content: str, file_sha: str, branch: str) -> None:
    """Update an existing file in the repository."""
    repository.update_file(filename, comment, file_content, sha=file_sha, branch=branch)

def delete_file(repository: Repository, filename: str, comment: str, file_sha: str, branch: str) -> None:
    """Delete a file from the repository."""
    repository.delete_file(filename, comment, file_sha, branch)

def git_pull(repository: Repository, branch: str) -> None:
        # Pull the latest changes from the remote origin
        try:
            subprocess.run(["git", "pull"], cwd="./", check=True, capture_output=True)
            log_info("Successfully pulled from remote")
        except Exception as e:
            log_error(f"Failed to pull from remote origin: {e}")
            raise Exception(f"Failed to pull from remote origin: {e}")

def save_webhook_data(data: dict) -> None:
    pass
