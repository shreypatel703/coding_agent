import pytest
from agents.pr_base_agent import PRTestAgent
from unittest.mock import MagicMock

@pytest.fixture
def setup_agent():
    agent = PRTestAgent()
    agent.run_tests = MagicMock(return_value={'passed': False, 'error_message': 'Sample error'})
    agent.fix_failed_test = MagicMock(return_value=True)
    return agent

@pytest.fixture
def mock_repository():
    return MagicMock()

@pytest.fixture
def mock_test_proposals():
    return [
        {'filename': 'test_sample.py'}
    ]


def test_test_and_fix_tests_success(setup_agent, mock_repository, mock_test_proposals):
    setup_agent.test_and_fix_tests(mock_repository, 'head_ref', mock_test_proposals)
    assert setup_agent.run_tests.call_count == 1
    assert setup_agent.fix_failed_test.call_count == 1


def test_test_and_fix_tests_failure(setup_agent, mock_repository, mock_test_proposals):
    setup_agent.run_tests.return_value = {'passed': False, 'error_message': 'Fail'}
    setup_agent.fix_failed_test.return_value = False
    result = setup_agent.test_and_fix_tests(mock_repository, 'head_ref', mock_test_proposals)
    assert setup_agent.run_tests.call_count == 1
    assert setup_agent.fix_failed_test.call_count == 1
    assert result[0]['passed'] == False
    assert result[0]['error_message'] == 'Fail'