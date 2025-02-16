import pytest
from utils.logging_utils import log_info, log_debug, log_error

class MockLogging:
    def info(self, message):
        print(f"INFO: {message}")
    def debug(self, message):
        print(f"DEBUG: {message}")
    def error(self, message):
        print(f"ERROR: {message}")

@pytest.fixture(autouse=True)
def mock_logging(mocker):
    mocker.patch('utils.logging_utils.logging', new=MockLogging())

def test_log_info():
    log_info('This is an info message')  # Should output to the console


def test_log_debug():
    log_debug('This is a debug message')  # Should output to the console


def test_log_error():
    log_error('This is an error message', Exception('Test Exception'))  # Should output to the console


# Run the tests with:
# pytest tests/unit/test_logging_utils.py

