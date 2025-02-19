import json
from utils.github_utils import getFileContent
from custom_types.base_types import GitHubFile

FILE_SIZE_THRESHOLD = 32000

def read_json(file_path: str):
    """Read JSON data from a file."""
    with open(file_path, "r") as f:
        return json.load(f)

def write_json(file_path: str, data):
    """Write JSON data to a file."""
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

def get_github_file(file, repository, ref):
    """Extract file details, including content and exclusion logic."""
    content = getFileContent(repository, file, ref)
    exclude = content and len(content) >= FILE_SIZE_THRESHOLD

    return GitHubFile(
        filename=file.filename,
        patch=file.patch,
        status=file.status,
        additions=file.additions,
        deletions=file.deletions,
        excluded=exclude,
        content=content
    )
