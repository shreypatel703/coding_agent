import pytest
from unittest.mock import MagicMock
from agents.pr_base_agent import PRBaseAgent
from utils.github_utils import Github


@pytest.fixture
def mock_github_client(mocker):
    mock = mocker.patch('utils.github_utils.Github')
    mock.get_repo.return_value = 'mock_repo'  # Provide a mock repository name or object
    return mock

@pytest.fixture
def setup_agent():
    agent = PRBaseAgent()
    return agent


def test_handle_pull_request(mock_github_client, setup_agent):
    repository = mock_github_client.get_repo.return_value
    pull_number = 1
    head_ref = 'main'

    # Mock the methods to return test data
    mock_github_client.get_pull_request_files.return_value = [
        MagicMock(filename='file1.py', status='modified'),
        MagicMock(filename='file2.py', status='added')
    ]
    mock_github_client.get_pull_request_commits.return_value = ['Commit Message']

    # Call the method under test
    files, commits = setup_agent.handle_pull_request(repository, pull_number, head_ref)

    # Assertions
    assert len(files) == 2  # Ensure the number of files returned is correct
    assert commits == ['Commit Message']  # Ensure the commits returned is correct
    mock_github_client.get_pull_request_files.assert_called_once_with(repository, pull_number)
    mock_github_client.get_pull_request_commits.assert_called_once_with(repository, pull_number)
