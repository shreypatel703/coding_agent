import pytest
from unittest.mock import patch, MagicMock
from PR_agent import generate_text, parseReviewXml, analyzeCode

@pytest.fixture
def mock_openai_response():
    """Fixture to mock the OpenAI API response."""
    return MagicMock(choices=[{"message": {"content": "mocked response"}}])

def test_generate_text(mock_openai_response):
    """Test the generate_text function."""
    with patch('PR_agent.client.chat.completions.create', return_value=mock_openai_response):
        response = generate_text("Test prompt")
        assert response == "mocked response"

def test_parseReviewXml():
    """Test the parseReviewXml function."""
    xml_input = """
    <review>
        <summary>Test summary.</summary>
        <fileAnalyses>
            <file>
                <path>test/path</path>
                <analysis>Test analysis.</analysis>
            </file>
        </fileAnalyses>
        <overallSuggestions>
            <suggestion>Test suggestion.</suggestion>
        </overallSuggestions>
    </review>
    """
    expected_output = {
        "summary": "Test summary.",
        "fileAnalyses": [
            {"path": "test/path", "analysis": ["Test analysis."]}
        ],
        "overallSuggestions": ["Test suggestion."]
    }
    assert parseReviewXml(xml_input) == expected_output

def test_analyzeCode(mock_openai_response):
    """Test integration of analyzeCode with mocked functions."""
    with patch('PR_agent.generate_text', return_value="<review><summary>Summary</summary></review>") as mock_gen_text:
        result = analyzeCode("Test PR Title", [{"filename": "test.py", "patch": "", "status": "modified", "additions": 1, "deletions": 0}], ["Initial commit"])
        assert result['summary'] == "Summary"
        mock_gen_text.assert_called_once()