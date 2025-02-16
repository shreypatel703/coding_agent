import pytest
from unittest.mock import MagicMock
from base_agent import update_file, handlePullRequestBase

def test_update_file():
    # Given
    file_mock = MagicMock()
    file_mock.status = 'modified'
    file_mock.filename = 'test_file.py'
    file_mock.patch = '...'  
    file_mock.additions = 10
    file_mock.deletions = 0
    repository_mock = MagicMock()
    ref_mock = 'main'
    file_mock.content = 'some content'

    # When
    result = update_file(file_mock, repository_mock, ref_mock)

    # Then
    assert result['filename'] == 'test_file.py'
    assert result['status'] == 'modified'


def test_handle_pull_request_base():
    # Given
    repository_mock = MagicMock()
    pull_number = 1
    head_ref = 'main'
    repository_mock.get_pull.return_value.get_files.return_value = [file_mock]

    # When
    updated_files, commit_messages = handlePullRequestBase(repository_mock, pull_number, head_ref)

    # Then
    assert isinstance(updated_files, list)
    assert len(updated_files) > 0
