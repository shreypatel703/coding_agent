import os

# Base Directories
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AGENTS_DIR = os.path.join(PROJECT_ROOT, "agents")
UTILS_DIR = os.path.join(PROJECT_ROOT, "utils")
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
WEBHOOKS_DIR = os.path.join(PROJECT_ROOT, "webhooks")
AUTH_DIR = os.path.join(PROJECT_ROOT, "auth")

# GitHub API Constants
GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "your_default_secret")

# Webhook Event Types
GITHUB_EVENT_PULL_REQUEST = "pull_request"
GITHUB_EVENT_ISSUE_COMMENT = "issue_comment"
GITHUB_EVENT_PUSH = "push"

# Pull Request Actions
PR_ACTION_OPENED = "opened"
PR_ACTION_LABELED = "labeled"

# Labels for PR Actions
LABEL_AGENT_REVIEW_PR = "agent-review-pr"
LABEL_AGENT_GENERATE_TESTS = "agent-generate-tests"

# Logging & Debugging
LOG_FILE_PATH = os.path.join(PROJECT_ROOT, "logs", "app.log")
WEBHOOK_DATA_FILE = os.path.join(PROJECT_ROOT, "data.json")

# Flask Config
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1")

# Authentication
GITHUB_ACCESS_TOKEN = os.getenv("GITHUB_ACCESS_TOKEN", "your_default_token")

# Other Constants
DEFAULT_ENCODING = "utf-8"