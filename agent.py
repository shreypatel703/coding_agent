from dotenv import load_dotenv
from flask import Flask, request, jsonify
import os
import json
from octokit import Octokit
from typing_extensions import TypedDict
from typing import Optional, List

from github_auth import generate_installation_token
from github import Github
from openai import OpenAI
import xml.etree.ElementTree as ET
import base64


load_dotenv()

OPENAI_API_KEY= os.getenv("OPENAI_API_KEY")
GITHUB_APP_ID=os.getenv("GITHUB_APP_ID")
GITHUB_PRIVATE_KEY=os.getenv("GITHUB_PRIVATE_KEY")
GITHUB_INSTALLATION_ID=os.getenv("GITHUB_INSTALLATION_ID")
WEBHOOK_PROXY_URL=os.getenv("WEBHOOK_PROXY_URL")

if not(GITHUB_APP_ID and GITHUB_PRIVATE_KEY and GITHUB_INSTALLATION_ID):
    raise Exception(f"""Missing required environment variables:
    APP_ID: ${GITHUB_APP_ID}
    PRIVATE_KEY: ${GITHUB_PRIVATE_KEY}
    INSTALLATION_ID: ${GITHUB_INSTALLATION_ID}""" )

if not OPENAI_API_KEY:
    raise Exception("Missing OPENAI_API_KEY environment variable.")


#TODO: Setup OCTOKit
installation_token = generate_installation_token(GITHUB_APP_ID, GITHUB_INSTALLATION_ID)
g = Github(installation_token)
client = OpenAI(api_key=OPENAI_API_KEY)
#TODO: setup OpenAI


class FileChange(TypedDict):
    filename: str
    patch: str
    status: str   # The status of the file (modified, added, removed, etc.)
    additions: int    # Number of lines added
    deletions: int    # Number of lines deleted
    content: Optional[str] #The actual current content of the file (Base64-decoded)
    

class FileAnalysis(TypedDict):
    path: str  # The path to the file being discussed
    analysis: str  # The AI's analysis for that file
class CodeAnalysis(TypedDict):
    summary: str
    fileAnalyses: List[FileAnalysis]
    overallSuggestions: List[str]



def generate_text(prompt: str):
    # Make an API call to OpenAI to generate text
    response = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="gpt-4o-mini",
    )
    response_message = response.choices[0].message.content
    return response_message


def parseReviewXml(text):
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


def analyzeCode(title: str, updated_files: list, commit_messages: list):
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



def postPlaceholderComment(owner: str, repo: str, pullNumber: int):
    
    
    repository = g.get_repo(f"{owner}/{repo}")

    # Post a comment on the PR
    comment = repository.get_issue(pullNumber).create_comment(
        "PR Review Bot is analyzing your changes... Please wait."
    )

    return comment

def updateCommentWithReview(owner, repo, comment, analysis):
    analyses = []
    for file in analysis["fileAnalyses"]:
        s = f"### {file['path']}\n"
        d = "\n".join([f" - {ana}" for ana in file["analysis"]])
        analyses.append(s+d)

    suggestions = "\n".join([f"- {s}" for s in analysis['overallSuggestions']])
    print(analyses)
    print(suggestions)
    new_text= """# Pull Request Review
## Summary
{summary}

## File Analyses
{analysis}

## Suggestions
{suggestions}
""".format(summary=analysis["summary"], analysis="\n".join(analyses), suggestions=suggestions)
    comment.edit(new_text)

def update_file(file, repository, ref):
    content = None
    if file.status != "removed":
        try:
            file_content = repository.get_contents(file.filename, ref)
            # Decode base64 content
            if hasattr(file_content, "content") and isinstance(file_content.content, str):
                print(file.content)
                content = base64.b64decode(file_content.content).decode("utf-8")

        except Exception as e:  
            print(f"Error retrieving content for {file.filename}:", e)
    return {
        "filename": file.filename,
        "patch": file.patch,
        "status": file.status,
        "additions": file.additions,
        "deletions": file.deletions,
        "content": content
    }

def handlePullRequestOpened(payload):
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    pullNumber = payload["pull_request"]["number"]
    title = payload["pull_request"]["title"]
    headRef = payload["pull_request"]["head"]["sha"]
    
    try:
        placeholder_comment = postPlaceholderComment(owner, repo, pullNumber)
        print(placeholder_comment)
        repository = g.get_repo(f"{owner}/{repo}")
        # Post a comment on the PR
        files = repository.get_pull(pullNumber).get_files()
        
        updated_files = [update_file(f, repository, headRef) for f in files]
        
        # TODO: Get Commit Messages
        commits = repository.get_pull(pullNumber).get_commits()
        commit_messages = [c.commit.message for c in commits]

        analysis = analyzeCode(title, updated_files, commit_messages)
        
        updateCommentWithReview(owner, repository, placeholder_comment, analysis)

        print(f"Submitted code review for PR #${pullNumber} in ${owner}/${repo}")
    except Exception as e:
        print(e)
        return -1


app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Hello World"


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json  # Get JSON payload
    # print("Received Webhook Data:", json.dumps(data, indent=4))
    with open("data.json", "w") as f:
        json.dump(data,f, indent=4)
    try:
        # The event type is in the header. We're primarily looking for "pull_request" events.
        eventType = data.get("pull_request", None)

        # For a "pull_request" event, if the action is "opened", we handle it with our function above.
        if eventType and data.get("action", None) == "opened":
            handlePullRequestOpened(data)
        return jsonify({"message": "OK!"}), 200
    except Exception as error:
        print("Error processing webhook:", error)
        return jsonify({"message": "Internal Server Error"}), 500
    
    return jsonify({"message": "Webhook received!"}), 200

if __name__ == '__main__':
    app.run(port=5000, debug=True)

