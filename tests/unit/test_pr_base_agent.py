import pytest
from agents.pr_base_agent import PRBaseAgent
from utils.github_utils import Github

@pytest.fixture
def mock_github_client(mocker):
    mock = mocker.patch('utils.github_utils.Github')
    return mock


# Mocking the methods for getting repo and PR details correctly.

def test_handle_pull_request(mock_github_client):
    mock_repo = mocker.Mock()
    mock_github_client.get_repo.return_value = mock_repo

    agent = PRBaseAgent()
    pull_number = 123
    head_ref = 'main'

    # Mock the methods to return test data
    mock_repo.get_pull.return_value.get_files.return_value = [
        {'filename': 'file1.py', 'status': 'modified'},
        {'filename': 'file2.py', 'status': 'added'}
    ]
    mock_repo.get_pull.return_value.get_commits.return_value = ['Commit message']

    files, commits = agent.handle_pull_request(mock_repo, pull_number, head_ref)

    assert len(files) == 2
    assert commits == ['Commit message']
    mock_repo.get_pull.return_value.get_files.assert_called_once()
    mock_repo.get_pull.return_value.get_commits.assert_called_once()