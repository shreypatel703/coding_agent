import pytest
from webhook.webhook_handler import process_webhook
from unittest.mock import patch


def test_process_webhook_pull_request_opened():
    event = "pull_request"
    data = {
        "action": "opened",
        "repository": {},
        "pull_request": {}
    }
    with patch('agents.pr_base_agent.PRCommentAgent.handle_pull_request_opened') as mock_handle_pr:
        response = process_webhook(event, data)
        assert mock_handle_pr.called
        assert response[0]['message'] == 'OK!'
        assert response[1] == 200


def test_process_webhook_failure():
    event = "pull_request"
    data = {
        "action": "opened",
        "repository": {},
        "pull_request": {}
    }
    with patch('agents.pr_base_agent.PRCommentAgent.handle_pull_request_opened', side_effect=Exception('Failure')):
        response = process_webhook(event, data)
        assert response[0]['message'] == 'PR review failed'
        assert response[1] == 500