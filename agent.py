from dotenv import load_dotenv
from flask import Flask, request, jsonify
import os
import json

def handlePullRequestOpened(payload):
    owner = payload.repository.owner.login
    repo = payload.repository.name
    pullNumber = payload.pull_request.number
    title = payload.pull_request.title
    headRef = payload.pull_request.head.sha
    print("owner",owner)
    print("repo", repo)
    print("pullNumber", pullNumber)
    print("title", title)
    print("headRef", headRef)





app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Hello World"


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json  # Get JSON payload
    print("Received Webhook Data:", json.dumps(data, indent=4))
    with open("data.json", "w") as f:
        json.dump(f, data, indent=4)
    try:
        # The event type is in the header. We're primarily looking for "pull_request" events.
        eventType = data.headers["x-github-event"]
        payload = data.body

        # For a "pull_request" event, if the action is "opened", we handle it with our function above.
        if eventType == "pull_request" and payload.action == "opened":
            handlePullRequestOpened(payload)
        return jsonify({"message": "OK!"}), 200
    except Exception as error:
        print("Error processing webhook:", error)
        return jsonify({"message": "Internal Server Error"}), 500
    
    return jsonify({"message": "Webhook received!"}), 200

if __name__ == '__main__':
    app.run(port=5000, debug=True)

