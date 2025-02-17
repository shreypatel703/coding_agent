import pytest
from prompts.fix_test_prompt import generate_fix_response
from unittest.mock import patch


def test_generate_fix_response_success():
    original_content = 'def test_example():\n    assert True'
    error_message = 'AssertionError'
    
    with patch('utils.llm_utils.LLMHandler.generate_response', return_value={'fixed_content': 'def test_example():\n    assert False'}):
        response = generate_fix_response(original_content, error_message)
        assert response.fixed_content == 'def test_example():\n    assert False'
+
+
+def test_generate_fix_response_failure():
+    original_content = 'def test_example():\n    assert True'
+    error_message = 'AssertionError'
+    
+    with patch('utils.llm_utils.LLMHandler.generate_response', side_effect=Exception('API failure')):
+        response = generate_fix_response(original_content, error_message)
+        assert response is None