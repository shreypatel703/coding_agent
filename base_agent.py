import base64
from github import Github
from github_auth import generate_installation_token, getFileContent
import json

FILE_SIZE_THRESHOLD = 32000

installation_token = generate_installation_token()
g = Github(installation_token)

def update_file(file, repository, ref):
    content = getFileContent(file, repository, ref)
    exclude = False
    if content and len(content) >= FILE_SIZE_THRESHOLD:
        exclude = True
    return {
        "filename": file.filename,
        "patch": file.patch,
        "status": file.status,
        "additions": file.additions,
        "deletions": file.deletions,
        "excluded": exclude,
        "content": content
    }


def handlePullRequestBase(repository, pullNumber, headRef):
    # Post a comment on the PR
    files = repository.get_pull(pullNumber).get_files()
    
    updated_files = [update_file(f, repository, headRef) for f in files]
    with open("file.json", "w") as f:
        json.dump(updated_files, f, indent=4)
    # TODO: Get Commit Messages
    commits = repository.get_pull(pullNumber).get_commits()
    commit_messages = [c.commit.message for c in commits]

    return updated_files, commit_messages