from dotenv import load_dotenv
from flask import Flask, request, jsonify
import os
import json
from octokit import Octokit
from typing_extensions import TypedDict
from typing import Optional, List

from github_auth import generate_installation_token
from github import Github


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
installation_token = generate_installation_token(GITHUB_APP_ID, GITHUB_PRIVATE_KEY)
g = Github(installation_token)
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



def postPlaceholderComment(owner: str, repo: str, pullNumber: int):

    data = octokit.issues.createComment({
        "owner": owner,
        "repo": repo,
        "issue_number": pullNumber,
        "body": "PR Review Bot is analyzing your changes... Please wait."
    })

    return data.get(id)


def handlePullRequestOpened(payload):
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    pullNumber = payload["pull_request"]["number"]
    title = payload["pull_request"]["title"]
    headRef = payload["pull_request"]["head"]["sha"]
    
    try:
        postPlaceholderComment(owner, repo, pullNumber)
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
    print("Received Webhook Data:", json.dumps(data, indent=4))
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

