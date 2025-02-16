import json
import base64
from github import Github
from auth.github_auth import generate_installation_token

# Initialize GitHub Client
installation_token = generate_installation_token()
g = Github(installation_token)

def get_repository(owner: str, repo_name: str):
    """Fetch the repository object."""
    return g.get_repo(f"{owner}/{repo_name}")

def get_pull_request(repository, pull_number: int):
    """Fetch the pull request object."""
    return repository.get_pull(pull_number)

def get_pull_request_files(repository, pull_number: int):
    """Fetch the files modified in a PR."""
    return get_pull_request(repository, pull_number).get_files()

def get_pull_request_commits(repository, pull_number: int):
    """Fetch the commit messages of a PR."""
    return [commit.commit.message for commit in get_pull_request(repository, pull_number).get_commits()]

def post_comment(repository, pull_number: int, message: str):
    """Post a comment on a PR."""
    return repository.get_issue(pull_number).create_comment(message)

def update_comment(comment, message: str):
    """Update an existing comment."""
    comment.edit(message)

def getFileContent(repository, file, ref):
    if file.status == "removed":
        return None
    
    file_content = repository.get_contents(file.filename, ref)
    
    # Check if content exists and is in base64 encoded string format
    if hasattr(file_content, "content") and isinstance(file_content.content, str):
        return base64.b64decode(file_content.content).decode("utf-8")
    
    return None

def create_file(repository, filename, comment, file_content, branch):
    """Create a new file in the repository."""
    repository.create_file(filename, comment, file_content, branch=branch)

def update_file(repository, filename, comment, file_content, file_sha, branch):
    """Update an existing file in the repository."""
    repository.update_file(filename, comment, file_content, sha=file_sha, branch=branch)

def delete_file(repository, filename, comment, file_sha, branch):
    """Delete a file from the repository."""
    repository.delete_file(filename, comment, file_sha, branch)


def save_webhook_data(data):
    pass
