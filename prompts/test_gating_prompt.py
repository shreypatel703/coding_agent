from pydantic import BaseModel, ValidationError, Field
from typing import Any, Dict, Type, List
from typing_extensions import TypedDict, Optional
from utils.llm_utils import LLMHandler
from custom_types.base_types import GitHubFile, GithubTestFile, GitHubCommit, TestGatingDecision

class ExistingFiles(BaseModel):
    filename: str
    content: Optional[str]

class FileChangePrompt(BaseModel):
    filename: str
    patch: str
    status: str   # The status of the file (modified, added, removed, etc.)
    content: Optional[str] #The actual current content of the file (Base64-decoded)

class testGatingInput(BaseModel):
    title: str
    commits: List[str]
    changed_files: List[FileChangePrompt]
    existing_tests: List[ExistingFiles]


class testGatingOutput(BaseModel):
    shouldGenerateTests: bool = Field(..., description="True if new tests are needed, False otherwise")
    reasoning: str = Field(..., description="Provide reasoning for determination")
    recommendations: List[str] = Field(..., description="List of suggested test case changes as strings")

testGatingPrompt = """You are an expert in deciding if tests are needed for these changes.
You have the PR title, commits, and file diffs/content.

Title: {title}
Commits:
{commits}
Changed Files:
{changed_files}
Existing Tests:
{existing_tests}

"""

def generate_gating_response(title: str, updated_files: List[GitHubFile], commit_messages: List[GitHubCommit], existing_tests: List[GithubTestFile]) -> TestGatingDecision:
    try:
        file_changes= [FileChangePrompt(filename=f.filename, patch=f.patch, status=f.status, content=f.content) for f in updated_files if not f.excluded]
        existing_tests= [ExistingFiles(filename=f.filename, content=f.content) for f in existing_tests]
        commits = [commit.message for commit in commit_messages]

        openAI_config = {
            "model": "gpt-4o-mini"
        }
        input_data={
            "title": title,
            "commits": commits,
            "changed_files": file_changes,
            "existing_tests": existing_tests
        }
        openAI_handler = LLMHandler(model_config=openAI_config)
        openAI_handler.set_task_config("summarize_pr", prompt_template=testGatingPrompt, input_model=testGatingInput, output_model=testGatingOutput) 
        response = openAI_handler.generate_response("summarize_pr", **input_data)

        return TestGatingDecision(**response.model_dump())
    
    except Exception as e:
        print("Gating step failed:", e)
        return TestGatingDecision(shouldGenerateTests=False, reasoning=f"ERROR:{e}", recommendations="")