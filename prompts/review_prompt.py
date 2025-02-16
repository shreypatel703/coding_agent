from pydantic import BaseModel, ValidationError, Field
from typing import Any, Dict, Type, List
from typing_extensions import TypedDict, Optional
from utils.llm_utils import LLMHandler

class FileChange(TypedDict):
    filename: str
    patch: str
    status: str   # The status of the file (modified, added, removed, etc.)
    additions: int    # Number of lines added
    deletions: int    # Number of lines deleted
    content: Optional[str] #The actual current content of the file (Base64-decoded)

class FileChangePrompt(BaseModel):
    filename: str
    patch: str
    status: str   # The status of the file (modified, added, removed, etc.)
    content: Optional[str] #The actual current content of the file (Base64-decoded)

class CodeReviewInput(BaseModel):
    title: str
    commits: List[str]
    changed_files: List[FileChangePrompt]

class Analysis(BaseModel):
    file_path: str = Field(..., description="file_path")
    analysis: str = Field(..., description="Write analysis as regular paragraphs, not code blocks")

class CodeReviewOutput(BaseModel):
    summary: str = Field(..., description="Write a clear, concise paragraph summarizing the changes")
    file_analyses: List[Analysis]
    suggestions: List[str] = Field(..., description="List of suggestions as strings")

CodeReviewPrompt="""You are an expert code reviewer. Analyze these pull request changes and provide detailed feedback.
Write your analysis in clear, concise paragraphs. Do not use code blocks for regular text.
Format suggestions as single-line bullet points.

Context:
PR Title: {title}
Commit Messages: 
{commits}

Changed Files:
{changed_files}
"""

def generate_review_response(title: str, updated_files: List[FileChange], commit_messages: List[str]):
    try:
        file_changes= [FileChangePrompt(filename=f["filename"], patch=f["patch"], status=f["status"], content=f["content"]) for f in updated_files if f["excluded"] == False]
        
        openAI_config = {
            "model": "gpt-4o-mini"
        }
        input_data={
            "title": title,
            "commits":commit_messages,
            "changed_files": file_changes
            
        }
        print("a")
        openAI_handler = LLMHandler(model_config=openAI_config)
        print("b")
        openAI_handler.set_task_config("summarize_pr", prompt_template=CodeReviewPrompt, input_model=CodeReviewInput, output_model=CodeReviewOutput) 
        print("c")
        response = openAI_handler.generate_response("summarize_pr", **input_data)
        print("d")
        return response
    
    except Exception as error:
        print("Error generating AI review:", error)
        return {"summary": "Error", "fileAnalyses": [], "overallSuggestions": []}