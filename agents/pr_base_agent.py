# Standard library imports
import json
from typing import List, Dict
from typing_extensions import Optional, TypedDict
from dataclasses import dataclass
import pytest
import sys

# Local imports
from utils import github_utils
from utils.file_utils import update_file
from prompts.review_prompt import generate_review_response
from prompts.test_gating_prompt import generate_gating_response
from prompts.test_case_update_prompt import generate_test_case_response
from utils.logging_utils import log_info, log_error, log_debug
from prompts.fix_test_prompt import generate_fix_response

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

class TestResult(TypedDict):
    file_path:str
    passed: bool
    error_message: Optional[str] = None
    retry_count : int = 0

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
            return True
        except Exception as e:
            log_error(f"Error in PR Comment Agent: {e}")
            github_utils.update_comment(placeholder_comment, f"Error Generating Review")
            return False

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
    
    MAX_RETRIES = 3

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
            if not gating_result.shouldGenerateTests:
                log_info(f"Skipping test generation: {gating_result.reasoning}")
                github_utils.update_comment(placeholder_comment, f"Skipping test generation: {gating_result.reasoning}")
                return True

            test_proposals = self.generate_test_cases(title, updated_files, commit_messages, existing_tests, gating_result.recommendations)
            self.commitTestChanges(repository, head_ref, test_proposals)

            test_results = self.test_and_fix_tests(repository, head_ref, test_proposals)

            self.update_comment_with_test_results(placeholder_comment, head_ref, test_proposals, test_results)
            return True
        except Exception as e:
            log_error(f"Error in Test Generation Agent: {e}")
            github_utils.update_comment(placeholder_comment, f"Error Generating Tests")
            return False

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

    def test_and_fix_tests(self, repository, head_ref, test_proposals):
        """
        Tests all test files and fixes them if they fail
        """
        # Track test results and retry counts
        test_results: Dict[str, TestResult] = {}
        
        # Run and fix tests
        for proposal in test_proposals.test_proposals:
            test_file = proposal.filename
            while True:
                result = self.run_tests(test_file)
                
                if result.passed:
                    test_results[test_file] = result
                    break
                    
                current_retries = test_results.get(test_file, TestResult(test_file, False)).retry_count + 1
                if current_retries >= self.MAX_RETRIES:
                    log_error(f"Max retries reached for {test_file}")
                    test_results[test_file] = TestResult(test_file, False, result.error_message, current_retries)
                    break
                    
                # Attempt to fix the test
                log_info(f"Attempting to fix {test_file}, attempt {current_retries}")
                if self.fix_failed_test(test_file, result.error_message, repository, head_ref):
                    result.retry_count = current_retries
                    test_results[test_file] = result
                else:
                    log_error(f"Failed to fix {test_file}")
                    break
        return test_results

    def run_tests(self, test_file_path: str) -> TestResult:
        """
        Runs a specific test file using pytest
        
        Args:
            test_file_path: Path to the test file
            
        Returns:
            TestResult object with execution results
        """
        try:
            # Run pytest on the specific file and capture output
            result = pytest.main(["-v", test_file_path, "-p", "no:warnings"])
            
            # pytest.ExitCode.OK is 0 (all tests passed)
            passed = result == pytest.ExitCode.OK
            error_message = None if passed else self._get_test_error_output(test_file_path)
            
            return TestResult(
                file_path=test_file_path,
                passed=passed,
                error_message=error_message
            )
        except Exception as e:
            log_error(f"Error running tests in {test_file_path}: {str(e)}")
            return TestResult(
                file_path=test_file_path,
                passed=False,
                error_message=str(e)
            )

    def _get_test_error_output(self, test_file_path: str) -> str:
        """
        Runs pytest with detailed output to get error messages
        """
        import io
        from contextlib import redirect_stdout

        output = io.StringIO()
        with redirect_stdout(output):
            pytest.main(["-vv", test_file_path])
        return output.getvalue()

    def fix_failed_test(self, test_file_path: str, error_message: str, repository, head_ref) -> bool:
        """
        Attempts to fix a failed test using the LLM
        
        Args:
            test_file_path: Path to the failed test
            error_message: The error message from the test run
            repository: GitHub repository object
            head_ref: Branch reference
            
        Returns:
            Boolean indicating if fix was successful
        """
        try:
            # Get the current content of the failed test
            file_content = github_utils.getFileContent(repository, test_file_path, head_ref)
            
            # Generate fixed test content using LLM
            fixed_content = self.generate_test_fix(file_content, error_message)
            
            if fixed_content:
                # Update the test file with the fixed content
                file = repository.get_contents(test_file_path, ref=head_ref)
                github_utils.update_file(
                    repository,
                    test_file_path,
                    f"Fix test: {test_file_path}",
                    fixed_content,
                    file.sha,
                    head_ref
                )
                return True
            return False
        except Exception as e:
            log_error(f"Error fixing test {test_file_path}: {str(e)}")
            return False

    def generate_test_fix(self, original_content: str, error_message: str) -> str:
        """
        Uses LLM to generate fixed test content
        
        Args:
            original_content: Original test file content
            error_message: Error message from the failed test
            
        Returns:
            Fixed test content or None if unable to fix
        """
        log_info(f"Generating test fix for {original_content}")
        fixed_content = generate_fix_response(original_content, error_message)
        return fixed_content.fixed_content
    
    def update_comment_with_test_results(self, placeholder_comment, head_ref, new_test_proposals, test_results: Dict[str, TestResult]):
        """
        Updates the PR comment with test generation and execution results
        """
        test_status = []
        for proposal in new_test_proposals.test_proposals:
            result = test_results.get(proposal.filename)
            if result:
                status = "✅ PASSED" if result.passed else f"❌ FAILED (after {result.retry_count} attempts)"
                error_info = f"\n  Error: {result.error_message}" if not result.passed else ""
                test_status.append(f"- **{proposal.filename}**: {status}{error_info}")
            else:
                test_status.append(f"- **{proposal.filename}**: ⚠️ Not executed")

        test_status_str = "\n".join(test_status)
        body = f"""### AI Test Generator
Test files on branch '{head_ref}':
{test_status_str}

*(Pull from that branch to see & modify them.)*"""
        github_utils.update_comment(placeholder_comment, body)