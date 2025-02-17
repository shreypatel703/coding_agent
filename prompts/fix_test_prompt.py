from utils.llm_utils import LLMHandler
from utils.logging_utils import log_error
from pydantic import BaseModel
from typing import Optional

FixTestPrompt = """
You are a helpful assistant that can fix test cases.
You will be given a test case and an error message.
You will need to fix the test case.
You will need to return the fixed test case.
If you cannot fix the test case, return None.

Here is the test case:
{test_content}

Here is the error message:
{error_message}
"""

class FixTestInput(BaseModel):
    test_content: str
    error_message: str

class FixTestOutput(BaseModel):
    fixed_content: Optional[str]





def generate_fix_response(original_content: str, error_message: str):
    try:
        openAI_config = {
            "model": "gpt-4o-mini"
        }
        input_data = {
            "test_content": original_content,
            "error_message": error_message
        }
        
        openAI_handler = LLMHandler(model_config=openAI_config)
        openAI_handler.set_task_config(
            "fix_test", 
            prompt_template=FixTestPrompt,
            input_model=FixTestInput,
            output_model=FixTestOutput
        )
        
        response = openAI_handler.generate_response("fix_test", **input_data)
        return response
        
    except Exception as error:
        log_error(f"Error generating test fix: {error}")
        return None