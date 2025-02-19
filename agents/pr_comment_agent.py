# Standard library imports
from typing import List, Dict, Any
from github.IssueComment import IssueComment

# Local imports
from agents.pr_base_agent import PRBaseAgent
from utils import github_utils
from prompts.review_prompt import generate_review_response
from utils.logging_utils import log_info, log_error, log_debug
from custom_types.base_types import GitHubFile, GitHubCommit, CodeReview

class PRCommentAgent(PRBaseAgent):
    """Agent that analyzes PRs and posts review comments"""

    def handle_pull_request_opened(self, payload: Dict[str, Any]) -> bool:
        """
        Handles a pull request opened event
        
        Args:
            payload: The webhook event payload
        """
        owner = payload["repository"]["owner"]["login"]
        repo_name = payload["repository"]["name"]
        pull_number = payload["pull_request"]["number"]
        title = payload["pull_request"]["title"]
        head_ref = payload["pull_request"]["head"]["ref"]

        log_info(f"Handling opened PR #{pull_number} in {owner}/{repo_name}")

        try:
            repository = github_utils.get_repository(owner, repo_name)
            placeholder_comment = github_utils.post_comment(repository, pull_number, "Review in progress...")

            updated_files, commit_messages = self.handle_pull_request(repository, pull_number, head_ref)
            analysis = self.analyze_code(title, updated_files, commit_messages)

            self.update_comment_with_review(placeholder_comment, analysis)
            return True
        except Exception as e:
            log_error(f"Error in PR Comment Agent: {e}")
            github_utils.update_comment(placeholder_comment, f"Error Generating Review")
            return False
    
    # TODO: Return type should be Type[CodeReviewOutput]
    def analyze_code(self, title: str, updated_files: List[GitHubFile], commit_messages: List[GitHubCommit]) -> CodeReview:
        """
        Analyzes the code changes in the PR
        
        Args:
            title: PR title
            updated_files: List of changed files
            commit_messages: List of commit messages
            
        Returns:
            Analysis response object
        """
        log_info(f"Analyzing code changes for PR: {title}")
        response = generate_review_response(title, updated_files, commit_messages)
        return response


    # TODO analysis should be Type[CodeReviewOutput]
    def update_comment_with_review(self, comment: IssueComment, analysis: CodeReview) -> None:
        """
        Updates the review comment with analysis results
        
        Args:
            comment: The comment to update
            analysis: The analysis results
        """
        log_info("Updating PR comment with review analysis")
        summary = analysis.summary
        print(analysis.file_analyses)
        analyses = "\n".join([f"### {f.file_path}\n - " + f.analysis for f in analysis.file_analyses])
        suggestions = "\n".join([f"- {s}" for s in analysis.suggestions])

        body = f"""# Pull Request Review\n## Summary\n{summary}\n\n## File Analyses\n{analyses}\n\n## Suggestions\n{suggestions}\n"""
        github_utils.update_comment(comment, body)

