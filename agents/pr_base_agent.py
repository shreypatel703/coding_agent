# Standard library imports
import json
from typing import List
from typing_extensions import Optional, TypedDict

# Local imports
from utils.file_utils import update_file
from prompts.review_prompt import generate_review_response
from prompts.test_gating_prompt import generate_gating_response
from prompts.test_case_update_prompt import generate_test_case_response
from utils import github_utils
from utils.logging_utils import log_info, log_error, log_debug

# Maximum file size threshold in bytes
FILE_SIZE_THRESHOLD = 32000

class FileChange(TypedDict):
    """Represents a file change in a pull request"""
    filename: str
    patch: str
    status: str   # The status of the file (modified, added, removed, etc.)
    additions: int    # Number of lines added
    deletions: int    # Number of lines deleted
    content: Optional[str] #The actual current content of the file (Base64-decoded)

class PRBaseAgent:
    """Base class for pull request agents that handle PR events"""
    def __init__(self):
        pass

    def handle_pull_request(self, repository, pull_number, head_ref):
        """
        Fetches files and commits for a pull request
        
        Args:
            repository: The GitHub repository object
            pull_number: The PR number
            head_ref: The head branch reference
            
        Returns:
            Tuple of (files, commits)
        """
        log_info(f"Fetching files and commits for PR #{pull_number}")
        files = [update_file(f, repository, head_ref) for f in github_utils.get_pull_request_files(repository, pull_number)]
        commits = github_utils.get_pull_request_commits(repository, pull_number)
        return files, commits

class PRCommentAgent(PRBaseAgent):
    """Agent that analyzes PRs and posts review comments"""
    
    def analyze_code(self, title: str, updated_files: List[FileChange], commit_messages: List[str]) :
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

    def handle_pull_request_opened(self, payload):
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
        except Exception as e:
            log_error("Error handling PR", e)

    def update_comment_with_review(self, comment, analysis):
        """
        Updates the review comment with analysis results
        
        Args:
            comment: The comment to update
            analysis: The analysis results
        """
        log_info("Updating PR comment with review analysis")
        summary = analysis.summary
        analyses = "\n".join([f"### {f.file_path}\n - " + f.analysis for f in analysis.file_analyses])
        suggestions = "\n".join([f"- {s}" for s in analysis.suggestions])

        body = f"""# Pull Request Review\n## Summary\n{summary}\n\n## File Analyses\n{analyses}\n\n## Suggestions\n{suggestions}\n"""
        github_utils.update_comment(comment, body)

class PRTestAgent(PRBaseAgent):
    """Agent that handles test generation for pull requests"""
    
    def get_existing_test_files(self, repository, ref, dir_path="tests"):
        """
        Recursively fetches all test files from a repository
        
        Args:
            repository: The GitHub repository
            ref: Branch reference
            dir_path: Directory path to search for tests
            
        Returns:
            List of test file contents
        """
        log_info(f"Fetching existing test files from {dir_path}")
        files = []
        try:
            contents = repository.get_contents(dir_path)
            for item in contents:
                if item.type == "file":
                    files.append(github_utils.getFileContent(repository, item.path, ref))
                elif item.type == "folder":
                    files.extend(self.get_existing_test_files(repository, ref, item.path))
        except Exception as ex:
            log_error("Error fetching tests", ex)
        return files

    def handle_pull_request_for_test_agent(self, payload):
        """
        Handles test generation for a pull request
        
        Args:
            payload: The webhook event payload
        """
        owner = payload["repository"]["owner"]["login"]
        repo_name = payload["repository"]["name"]
        pull_number = payload["pull_request"]["number"]
        title = payload["pull_request"]["title"]
        head_ref = payload["pull_request"]["head"]["ref"]

        log_info(f"Handling test generation for PR #{pull_number} in {owner}/{repo_name}")

        try:
            repository = github_utils.get_repository(owner, repo_name)
            placeholder_comment = github_utils.post_comment(repository, pull_number, "Test analysis in progress...")

            updated_files, commit_messages = self.handle_pull_request(repository, pull_number, head_ref)
            existing_tests = self.get_existing_test_files(repository, head_ref)

            gating_result = self.gating_step(title, updated_files, commit_messages, existing_tests)
            if gating_result.shouldGenerateTests == False:
                log_info(f"Skipping test generation: {gating_result.reasoning}")
                github_utils.update_comment(placeholder_comment, f"Skipping test generation: {gating_result.reasoning}")
                return

            test_proposals = self.generate_test_cases(title, updated_files, commit_messages, existing_tests, gating_result.recommendations)
            self.commitTestChanges(repository, head_ref, test_proposals)
            self.update_comment_with_test_results(placeholder_comment, head_ref, test_proposals)
        except Exception as e:
            log_error("Error handling test PR", e)

    def gating_step(self, title, updated_files, commit_messages, existing_tests):
        """
        Determines if test generation should proceed
        
        Args:
            title: PR title
            updated_files: Changed files
            commit_messages: Commit messages
            existing_tests: Existing test files
            
        Returns:
            Gating response object
        """
        log_info("Performing test generation gating step")
        response = generate_gating_response(title, updated_files, commit_messages, existing_tests)
        return response

    def generate_test_cases(self, title, updated_files, commit_messages, existing_tests, recommendations):
        """
        Generates test cases for the changed files
        
        Args:
            title: PR title
            updated_files: Changed files
            commit_messages: Commit messages
            existing_tests: Existing test files
            recommendations: Test recommendations
            
        Returns:
            Test case proposals
        """
        log_info("Generating test cases")
        response=generate_test_case_response(title, updated_files, commit_messages, existing_tests, recommendations)
        return response

    def commitTestChanges(self, repository, head_ref, new_test_proposals):
        """
        Commits generated test files to the repository
        
        Args:
            repository: GitHub repository
            head_ref: Branch reference
            new_test_proposals: Generated test proposals
        """
        log_info("Committing generated test files")
        for proposal in new_test_proposals.test_proposals:
            log_debug(f"Processing test proposal: {proposal}")
            filename = proposal.filename
            test_content = proposal.testContent
            actions = proposal.actions
            for action in actions:
                if action.action == "create":
                    log_info(f"Creating new test file: {filename}")
                    github_utils.create_file(repository,filename, f"Add tests: {filename}", test_content, head_ref)
                if action.action == "update":
                    log_info(f"Updating test file: {filename}")
                    file = repository.get_contents(filename, ref=head_ref)
                    github_utils.update_file(repository,filename, f"Update tests: {filename}", test_content, file.sha, head_ref)
                if action.action == "rename":
                    old_file=action.old_filename
                    log_info(f"Renaming test file from {old_file} to {filename}")
                    file = repository.get_contents(old_file, ref=head_ref)
                    # Create the new file with the same content
                    github_utils.create_file(repository, filename, f"Renaming {old_file} to {filename}", test_content, head_ref)
                    # Delete the old file
                    github_utils.delete_file(repository, old_file, f"Removed old file {old_file} after renaming to {filename}", file.sha, head_ref)

    def update_comment_with_test_results(self, placeholder_comment, head_ref, new_test_proposals):
        """
        Updates the PR comment with test generation results
        
        Args:
            placeholder_comment: Comment to update
            head_ref: Branch reference
            new_test_proposals: Generated test proposals
        """
        log_info("Updating PR comment with test generation results")
        test_list = "\n".join([f"- **{proposal.filename}**" for proposal in new_test_proposals.test_proposals])

        # Construct the comment body
        if new_test_proposals:
            body = f"""### AI Test Generator
    \nAdded/updated these test files on branch '{head_ref}':
    \n{test_list}

    *(Pull from that branch to see & modify them.)*
    """
        else:
            body = "### AI Test Generator\n\n No test proposals were generated."
        
        github_utils.update_comment(placeholder_comment, body)