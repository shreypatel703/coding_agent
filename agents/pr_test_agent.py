# Standard library imports
from typing import List, Dict, Any
from github.Repository import Repository
from github.IssueComment import IssueComment
import pytest

# Local imports
from agents.pr_base_agent import PRBaseAgent
from utils import github_utils
from prompts.test_gating_prompt import generate_gating_response
from prompts.test_case_update_prompt import generate_test_case_response
from utils.logging_utils import log_info, log_error, log_debug
from prompts.fix_test_prompt import generate_fix_response
from custom_types.base_types import GitHubFile, GithubTestFile, GitHubCommit, TestGatingDecision, TestProposal, TestResult

class PRTestAgent(PRBaseAgent):
    """Agent that handles test generation for pull requests"""
    
    MAX_RETRIES = 3

    def handle_pull_request_for_test_agent(self, payload: Dict[str, Any]) -> bool:
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
            self.commitTestChanges(repository, head_ref, test_proposals, existing_tests)

            test_results = self.test_and_fix_tests(repository, head_ref, test_proposals)

            self.update_comment_with_test_results(placeholder_comment, head_ref, test_proposals, test_results)
            return True
        except Exception as e:
            log_error(f"Error in Test Generation Agent: {e}")
            github_utils.update_comment(placeholder_comment, f"Error Generating Tests")
            return False

    def get_existing_test_files(self, repository: Repository, ref: str, dir_path: str = "tests") -> List[GithubTestFile]:
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
                    files.append(GithubTestFile(filename=item.path, content=github_utils.getFileContent(repository, item.path, ref)))
                elif item.type == "folder":
                    files.extend(self.get_existing_test_files(repository, ref, item.path))
        except Exception as ex:
            log_error("Error fetching tests", ex)
        return files
    
    def gating_step(self, title: str, updated_files: List[GitHubFile], commit_messages: List[GitHubCommit], existing_tests: List[GithubTestFile]) -> TestGatingDecision:
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

    def generate_test_cases(self, title: str, updated_files: List[GitHubFile], commit_messages: List[GitHubCommit], existing_tests: List[str], recommendations: List[str]) -> List[TestProposal]:
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

    def commitTestChanges(self, repository: Repository, head_ref: str, new_test_proposals: List[TestProposal], existing_tests: List[GithubTestFile]) -> None:
        """
        Commits generated test files to the repository
        
        Args:
            repository: GitHub repository
            head_ref: Branch reference
            new_test_proposals: Generated test proposals
        """
        log_info("Committing generated test files")
        for proposal in new_test_proposals:
            log_debug(f"Processing test proposal: {proposal}")
            filename = proposal.filename
            test_content = proposal.testContent
            actions = proposal.actions
            for action in actions:
                if action.action == "create":
                    print([t.filename for t in existing_tests])
                    if filename in [t.filename for t in existing_tests]:
                        log_info(f"Test file {filename} already exists, skipping creation")
                        continue
                    log_info(f"Creating new test file: {filename}")
                    github_utils.create_file(repository,filename, f"Add tests: {filename}", test_content, head_ref)
                elif action.action == "update":
                    log_info(f"Updating test file: {filename}")
                    file = repository.get_contents(filename, ref=head_ref)
                    github_utils.update_file(repository,filename, f"Update tests: {filename}", test_content, file.sha, head_ref)
                elif action.action == "rename":
                    old_file=action.old_filename
                    log_info(f"Renaming test file from {old_file} to {filename}")
                    file = repository.get_contents(old_file, ref=head_ref)
                    # Create the new file with the same content
                    github_utils.create_file(repository, filename, f"Renaming {old_file} to {filename}", test_content, head_ref)
                    # Delete the old file
                    github_utils.delete_file(repository, old_file, f"Removed old file {old_file} after renaming to {filename}", file.sha, head_ref)

    def test_and_fix_tests(self, repository: Repository, head_ref: str, test_proposals: List[TestProposal]) -> Dict[str, TestResult]:
        """
        Tests all test files and fixes them if they fail
        """
        # Track test results and retry counts
        test_results: Dict[str, TestResult] = {}

        github_utils.git_pull(repository, head_ref)

        # Run and fix tests
        for proposal in test_proposals:
            test_file = proposal.filename
            retry_count = 0
            
            while True:
                result = self.run_tests(test_file)
                
                if result["passed"]:
                    test_results[test_file] = result
                    break
                
                retry_count += 1
                if retry_count >= self.MAX_RETRIES:
                    log_info(f"Max retries reached for {test_file}")
                    test_results[test_file] = TestResult({
                        "file_path": test_file,
                        "passed": False,
                        "error_message": result["error_message"],
                        "retry_count": retry_count
                    })
                    break
                    
                # Attempt to fix the test
                log_info(f"Attempting to fix {test_file}, attempt {retry_count}")
                if not self.fix_failed_test(test_file, result["error_message"], repository, head_ref):
                    log_info(f"Failed to fix {test_file}")
                    test_results[test_file] = TestResult({
                        "file_path": test_file,
                        "passed": False,
                        "error_message": result["error_message"],
                        "retry_count": retry_count
                    })
                    break
                github_utils.git_pull(repository, head_ref)

        return test_results

    def run_tests(self, test_file_path: str) -> Dict[str, Any]:
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
            
            return {
                "passed":passed,
                "error_message":error_message,
                }
        except Exception as e:
            log_error(f"Error running tests in {test_file_path}: {str(e)}")
            return {
                "passed":False,
                "error_message":str(e),
                }

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

    def fix_failed_test(self, test_file_path: str, error_message: str, repository: Repository, head_ref: str) -> bool:
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
            file_content = github_utils.get_file_content_by_filename(repository, test_file_path, head_ref)
            
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
            log_error(f"Error fixing test {test_file_path}:", str(e))
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
    
    def update_comment_with_test_results(self, placeholder_comment: IssueComment, head_ref: str, new_test_proposals: TestProposal, test_results: Dict[str, TestResult]):
        """
        Updates the PR comment with test generation and execution results
        """
        test_status = []
        for proposal in new_test_proposals:
            result = test_results.get(proposal.filename)
            if result:
                status = "✅ PASSED" if result['passed'] else f"❌ FAILED (after {result['retry_count']} attempts)"
                #error_info = f"\n  Error: {result['error_message']}" if not result['passed'] else ""
                test_status.append(f"- **{proposal.filename}**: {status}")
            else:
                test_status.append(f"- **{proposal.filename}**: ⚠️ Not executed")

        test_status_str = "\n".join(test_status)
        body = f"""### AI Test Generator
Test files on branch '{head_ref}':
{test_status_str}

*(Pull from that branch to see & modify them.)*"""
        github_utils.update_comment(placeholder_comment, body)