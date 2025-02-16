import json
from flask import Blueprint, request, jsonify
from utils.github_utils import save_webhook_data
from agents.pr_base_agent import PRCommentAgent, PRTestAgent
from utils.logging_utils import log_info, log_error

webhook_blueprint = Blueprint("webhook", __name__)

def process_webhook(event, data):
    """
    Processes incoming GitHub webhook events.
    
    :param event: The type of GitHub event (e.g., "pull_request").
    :param data: The JSON payload from GitHub.
    :return: JSON response with status code.
    """
    try:
        save_webhook_data(data)  # Save webhook data for debugging

        action = data.get("action")
        if event == "pull_request":
            if action == "opened":
                log_info("Handling PR opened event.")
                PRCommentAgent().handle_pull_request_opened(data)
            elif action == "labeled":
                label_name = data.get("label", {}).get("name")
                if label_name == "agent-review-pr":
                    log_info("Handling PR labeled for agent review.")
                    PRCommentAgent().handle_pull_request_opened(data)
                elif label_name == "agent-generate-tests":
                    log_info("Handling PR labeled for test generation.")
                    PRTestAgent().handle_pull_request_for_test_agent(data)

        return jsonify({"message": "OK!"}), 200
    except Exception as error:
        log_error(f"Error processing webhook: {error}")
        return jsonify({"message": "Internal Server Error"}), 500