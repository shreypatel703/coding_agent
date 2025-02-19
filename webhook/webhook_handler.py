import json
from flask import Blueprint, request, jsonify
from utils.github_utils import save_webhook_data
from agents.pr_comment_agent import PRCommentAgent
from agents.pr_test_agent import PRTestAgent
from utils.logging_utils import log_info, log_error

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
        if event == "pull_request" and (action == "opened" or action == "labeled"):
            log_info("Handling PR opened event.")
            
            # Run PR Comment Agent first
            comment_success = PRCommentAgent().handle_pull_request_opened(data)
            if not comment_success:
                log_error("PR Comment Agent failed to complete successfully")
                return jsonify({"message": "PR review failed"}), 500
            
            # Only proceed with test generation if comment agent succeeds
            log_info("Generating tests for the PR.")
            test_success = PRTestAgent().handle_pull_request_for_test_agent(data)
            if not test_success:
                log_error("Test Generation Agent failed to complete successfully")
                return jsonify({"message": "Test generation failed"}), 500

        return jsonify({"message": "OK!"}), 200
    except Exception as error:
        log_error(f"Error processing webhook: {error}")
        return jsonify({"message": "Internal Server Error"}), 500