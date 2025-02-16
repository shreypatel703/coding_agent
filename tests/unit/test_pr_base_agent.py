import pytest
from agents.pr_base_agent import PRBaseAgent

@pytest.fixture
def mock_github_client(mocker):
    mock = mocker.patch('utils.github_utils.Github')
    return mock

def test_handle_pull_request(mock_github_client):
    agent = PRBaseAgent()
    repository = mock_github_client.get_repo.return_value
    pull_number = 123
    head_ref = 'main'

    # Mock the methods to return test data
    mock_github_client.get_pull_request_files.return_value = [
        {'filename': 'file1.py', 'status': 'modified'},
        {'filename': 'file2.py', 'status': 'added'}
    ]
    mock_github_client.get_pull_request_commits.return_value = ['Commit message']

    files, commits = agent.handle_pull_request(repository, pull_number, head_ref)

    assert len(files) == 2
    assert commits == ['Commit message']
    mock_github_client.get_pull_request_files.assert_called_once_with(repository, pull_number)
    mock_github_client.get_pull_request_commits.assert_called_once_with(repository, pull_number)

