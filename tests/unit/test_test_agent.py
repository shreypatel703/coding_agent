import json
import pytest
from unittest.mock import MagicMock
from test_agent import gatingStep, updateTests


def test_gating_step():
    title = "Test PR"
    updated_files = [
        {"filename": "test_file.py", "status": "modified", "content": "..."}
    ]
    commit_messages = ["Commit 1", "Commit 2"]
    existing_test_files = []  
    result = gatingStep(title, updated_files, commit_messages, existing_test_files)
    assert isinstance(result, dict)
    assert "decision" in result


def test_update_tests():
    title = "Test PR"
    updated_files = []
    commit_messages = []
    existing_test_files = []  
    recommendations = "Add tests for new functions."
    result = updateTests(title, updated_files, commit_messages, existing_test_files, recommendations)
    assert isinstance(result, list)
