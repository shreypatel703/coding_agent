import pytest
from flask import json
from app import app


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_webhook_opened(client):
    payload = {
        "action": "opened",
        "repository": {
            "owner": {"login": "test_owner"},
            "name": "test_repo"
        },
        "pull_request": {
            "number": 1,
            "title": "Test PR",
            "head": {"ref": "main"}
        }
    }
    response = client.post('/webhook', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 200


def test_webhook_labeled(client):
    payload = {
        "action": "labeled",
        "repository": {
            "owner": {"login": "test_owner"},
            "name": "test_repo"
        },
        "pull_request": {
            "number": 1,
            "title": "Test PR",
            "head": {"ref": "main"},
            "labels": [{"name": "agent-review-pr"}]
        },
        "label": {"name": "agent-review-pr"}
    }
    response = client.post('/webhook', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 200
