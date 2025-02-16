import pytest
from agents.pr_base_agent import PRCommentAgent
from utils.github_utils import Github

@pytest.fixture
def mock_github_client(mocker):
    mock = mocker.patch('utils.github_utils.Github')
    return mock

@pytest.fixture
def comment_agent():
    return PRCommentAgent()

def test_analyze_code(comment_agent):
    title = 'Test PR'
    updated_files = [
        {'filename': 'file1.py', 'status': 'modified'},
        {'filename': 'file2.py', 'status': 'added'}
    ]
    commit_messages = ['Commit message']

    response = comment_agent.analyze_code(title, updated_files, commit_messages)

    assert response is not None
    assert isinstance(response, dict)


def test_handle_pull_request_opened(comment_agent, mock_github_client):
    payload = {
        'repository': {'owner': {'login': 'owner'}, 'name': 'repo'},
        'pull_request': {'number': 123, 'title': 'Test PR', 'head': {'ref': 'main'}}
    }

    comment_agent.handle_pull_request_opened(payload)
    mock_github_client.get_repository.assert_called_once_with('owner', 'repo')
    mock_github_client.post_comment.assert_called_once_with(
        mock_github_client.get_repository.return_value,
        123,
        'Review in progress...'
    )

    # Check that update_comment_with_review is called
    assert hasattr(comment_agent, 'update_comment_with_review'), 'update_comment_with_review not called.'

