import os
import json
import base64

import xml.etree.ElementTree as ET

from typing import Optional, List
from typing_extensions import TypedDict


from base_agent import g, handlePullRequestBase
from github_auth import postPlaceholderComment, updateComment
from llm import generate_text



class FileChange(TypedDict):
    filename: str
    patch: str
    status: str   # The status of the file (modified, added, removed, etc.)
    additions: int    # Number of lines added
    deletions: int    # Number of lines deleted
    content: Optional[str] #The actual current content of the file (Base64-decoded)
    

class FileAnalysis(TypedDict):
    path: str  # The path to the file being discussed
    analysis: List[str]  # The AI's analysis for that file
class CodeAnalysis(TypedDict):
    summary: str
    fileAnalyses: List[FileAnalysis]
    overallSuggestions: List[str]


def parseReviewXml(text:str):
    root = ET.fromstring(text)
    summary = root.find("summary").text
    file_analyses = []
    for file in root.find("fileAnalyses").findall("file"):
        path = file.find("path").text
        analysis = [x.text for x in file.findall("analysis")]
        file_analyses.append({
            "path": path,
            "analysis": analysis
        })
    suggestions = [s.text for s in root.find("overallSuggestions").findall("suggestion")]
    return {
        "summary": summary,
        "fileAnalyses": file_analyses,
        "overallSuggestions": suggestions
    }


def analyzeCode(title: str, updated_files: FileChange, commit_messages: list):
    commits = '\n'.join([f"- {msg}" for msg in commit_messages])
    changed_files = '\n'.join([json.dumps({
        "File": file["filename"],
        "Status": file["status"],
        "Diff": file["patch"],
        "Current Content": file.get("content","N/A")
    }) for file in updated_files])
    prompt = f"""You are an expert code reviewer. Analyze these pull request changes and provide detailed feedback.
Write your analysis in clear, concise paragraphs. Do not use code blocks for regular text.
Format suggestions as single-line bullet points.

Context:
PR Title: ${title}
Commit Messages: 
{commits}

Changed Files:
{changed_files}

Provide your review in the following XML format:
<review>
  <summary>Write a clear, concise paragraph summarizing the changes</summary>
  <fileAnalyses>
    <file>
      <path>file path</path>
      <analysis>Write analysis as regular paragraphs, not code blocks</analysis>
    </file>
  </fileAnalyses>
  <overallSuggestions>
    <suggestion>Write each suggestion as a single line</suggestion>
  </overallSuggestions>
</review>;"""

    try:
        text = generate_text(prompt)
        with open("xml.html", "w") as f:
            f.write(text)
        return parseReviewXml(text)
    except Exception as error:
        print("Error generating or parsing AI analysis:", error)
        return {
            "summary": "We were unable to analyze the code due to an internal error.",
            "fileAnalyses": [],
            "overallSuggestions": []
        }


def updateCommentWithReview(comment, analysis:CodeAnalysis):
    analyses = []
    for file in analysis["fileAnalyses"]:
        s = f"### {file['path']}\n"
        d = "\n".join([f" - {ana}" for ana in file["analysis"]])
        analyses.append(s+d)

    suggestions = "\n".join([f"- {s}" for s in analysis['overallSuggestions']])
    print(analyses)
    print(suggestions)
    body = """# Pull Request Review
## Summary
{summary}

## File Analyses
{analysis}

## Suggestions
{suggestions}
""".format(summary=analysis["summary"], analysis="\n".join(analyses), suggestions=suggestions)
    
    updateComment(comment, body)


def handlePullRequestOpened(payload):
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    pullNumber = payload["pull_request"]["number"]
    title = payload["pull_request"]["title"]
    headRef = payload["pull_request"]["head"]["ref"]
    
    try:
        repository = g.get_repo(f"{owner}/{repo}")

        placeholder_comment = postPlaceholderComment(repository, pullNumber, "PR Review Bot is analyzing your changes... Please wait.")
        
        updated_files, commit_messages = handlePullRequestBase(repository, pullNumber, headRef)

        analysis = analyzeCode(title, updated_files, commit_messages)
        
        updateCommentWithReview(placeholder_comment, analysis)

        print(f"Submitted code review for PR #${pullNumber} in ${owner}/${repo}")
    except Exception as e:
        print(e)
        return -1




