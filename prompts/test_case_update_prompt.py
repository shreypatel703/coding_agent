from pydantic import BaseModel, ValidationError, Field
from typing import Any, Dict, Type, List
from typing_extensions import TypedDict, Optional, Literal
from utils.llm_utils import LLMHandler

class FileChange(TypedDict):
    filename: str
    patch: str
    status: str   # The status of the file (modified, added, removed, etc.)
    additions: int    # Number of lines added
    deletions: int    # Number of lines deleted
    content: Optional[str] #The actual current content of the file (Base64-decoded)

class ExistingFiles(BaseModel):
    filename: str
    content: Optional[str]

class FileChangePrompt(BaseModel):
    filename: str
    patch: str
    status: str   # The status of the file (modified, added, removed, etc.)
    content: Optional[str] #The actual current content of the file (Base64-decoded)

class testUpdateInput(BaseModel):
    title: str
    commits: List[str]
    changed_files: List[FileChangePrompt]
    existing_tests: List[ExistingFiles]
    recommendations: List[str]

class Action(BaseModel):
    action: Literal["create", "update", "rename"] = Field(..., description="Possible Actions that can be performed on file: create new file, update existing file, rename exisiting file")
    oldFilename: Optional[str] = Field(None, description="If acion is rename, specify the old file name")

class Proposal(BaseModel):
    filename: str = Field(..., description="Relative File Path. Should be either `tests/unit/__.py` or`tests/integration/__.py`")
    testType: str = Field(..., description="Type of test: 'unit' or 'integration'")
    testContent: str = Field(..., description="Python file containing test")
    actions: List[Action]

class testUpdateOutput(BaseModel):
    test_proposals: List[Proposal] = Field(..., description="List of Proposed changes, Return empty list if no proposals")


testUpdatePrompt = """
    You are an expert software developer specializing in writing tests for a Python codebase.

    You may use the recommendation below and/or go beyond it.

    Recommendation: {recommendations}

    Remember - you only generate tests for Python code. This includes things like functions, classes, modules, and scripts. You do not generate tests for front-end code such as JavaScript or UI components.

    Rules for naming test files:
    1) If a file contains a Python module, the test filename MUST follow the convention: "test_<module_name>.py".
    2) If the file being tested is inside a package, the test file should reside in the corresponding `tests/` directory, mirroring the structure of the source code.
    3) If an existing test file has the wrong name, propose renaming it.
    4) If updating an existing test file that has the correct name, update it in place.

    We have two test categories:
    (1) Unit tests (pytest/unittest) in `tests/unit/`
    (2) Integration tests in `tests/integration/`

    If an existing test already covers related functionality, prefer updating it rather than creating a new file. Return final content for each file you modify or create.

    Other rules:
    - Mock external dependencies and database calls where necessary.
    - Follow best practices for structuring test functions (given/when/then, AAA - Arrange, Act, Assert).
    - Use pytest fixtures where appropriate for reusable setup/teardown logic.

    Title: ${title}
    Commits:
    {commits}
    Changed Files:
    ${changed_files}
    Existing Tests:
    ${existing_tests}
    """

def generate_test_case_response(title: str, updated_files: List[FileChange], commit_messages: List[str], existing_tests, recommendations):
    try:
        file_changes= [FileChangePrompt(filename=f["filename"], patch=f["patch"], status=f["status"], content=f["content"]) for f in updated_files if f["excluded"] == False]
        existing_tests= [ExistingFiles(filename=f["filename"], content=f["content"]) for f in existing_tests]

        openAI_config = {
            "model": "gpt-4o-mini"
        }
        input_data={
            "title": title,
            "commits":commit_messages,
            "changed_files": file_changes,
            "existing_tests": existing_tests,
            "recommendations": recommendations
        }
        openAI_handler = LLMHandler(model_config=openAI_config)
        openAI_handler.set_task_config("summarize_pr", prompt_template=testUpdatePrompt, input_model=testUpdateInput, output_model=testUpdateOutput) 
        response = openAI_handler.generate_response("summarize_pr", **input_data)
        return response
    except Exception as e:
        print("Test Update step failed:", e)
        return testUpdateOutput(test_proposals=[])