import json
from flask import Flask, request, jsonify
from PR_agent import handlePullRequestOpened
from test_agent import handlePullRequestForTestAgent

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
        event = request.headers.get("X-GitHub-Event")
        action = data.get("action", None)
        # The event type is in the header. We're primarily looking for "pull_request" events.
        # For a "pull_request" event, if the action is "opened", we handle it with our function above.
        if event == "pull_request":
            if action == "opened":
                handlePullRequestOpened(data)
            elif action == "labeled":
                labelName = data.get("label").get("name")
                if labelName == "agent-review-pr":
                    handlePullRequestOpened(data)
                elif labelName == "agent-generate-tests":
                    handlePullRequestForTestAgent(data)


        return jsonify({"message": "OK!"}), 200
    except Exception as error:
        print("Error processing webhook:", error)
        return jsonify({"message": "Internal Server Error"}), 500
    

if __name__ == '__main__':
    app.run(port=5000, debug=True)