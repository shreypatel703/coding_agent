import json
from typing import List
from typing_extensions import Optional, TypedDict

from utils.file_utils import update_file
from prompts.review_prompt import generate_review_response
from prompts.test_gating_prompt import generate_gating_response
from prompts.test_case_update_prompt import generate_test_case_response
from utils import github_utils
FILE_SIZE_THRESHOLD = 32000

class FileChange(TypedDict):
    filename: str
    patch: str
    status: str   # The status of the file (modified, added, removed, etc.)
    additions: int    # Number of lines added
    deletions: int    # Number of lines deleted
    content: Optional[str] #The actual current content of the file (Base64-decoded)

class PRBaseAgent:
    def __init__(self):
        pass

    def handle_pull_request(self, repository, pull_number, head_ref):
        files = [update_file(f, repository, head_ref) for f in github_utils.get_pull_request_files(repository, pull_number)]
        commits = github_utils.get_pull_request_commits(repository, pull_number)
        return files, commits

class PRCommentAgent(PRBaseAgent):
    def analyze_code(self, title: str, updated_files: List[FileChange], commit_messages: List[str]) :
        response = generate_review_response(title, updated_files, commit_messages)
        return response


    def handle_pull_request_opened(self, payload):
        owner = payload["repository"]["owner"]["login"]
        repo_name = payload["repository"]["name"]
        pull_number = payload["pull_request"]["number"]
        title = payload["pull_request"]["title"]
        head_ref = payload["pull_request"]["head"]["ref"]

        try:
            repository = github_utils.get_repository(owner, repo_name)
            placeholder_comment = github_utils.post_comment(repository, pull_number, "Review in progress...")

            updated_files, commit_messages = self.handle_pull_request(repository, pull_number, head_ref)
            analysis = self.analyze_code(title, updated_files, commit_messages)

            self.update_comment_with_review(placeholder_comment, analysis)
        except Exception as e:
            print("Error handling PR:", e)

    def update_comment_with_review(self, comment, analysis):
        summary = analysis.summary
        analyses = "\n".join([f"### {f.file_path}\n - " + f.analysis for f in analysis.file_analyses])
        suggestions = "\n".join([f"- {s}" for s in analysis.suggestions])

        body = f"""# Pull Request Review\n## Summary\n{summary}\n\n## File Analyses\n{analyses}\n\n## Suggestions\n{suggestions}\n"""
        github_utils.update_comment(comment, body)

class PRTestAgent(PRBaseAgent):
    def get_existing_test_files(self, repository, ref, dir_path="tests"):
        files = []
        try:
            contents = repository.get_contents(dir_path)
            for item in contents:
                if item.type == "file":
                    files.append(github_utils.getFileContent(repository, item.path, ref))
                elif item.type == "folder":
                    files.extend(self.get_existing_test_files(repository, ref, item.path))
        except Exception as ex:
            print("Error fetching tests:", ex)
        return files

    def handle_pull_request_for_test_agent(self, payload):
        owner = payload["repository"]["owner"]["login"]
        repo_name = payload["repository"]["name"]
        pull_number = payload["pull_request"]["number"]
        title = payload["pull_request"]["title"]
        head_ref = payload["pull_request"]["head"]["ref"]

        try:
            repository = github_utils.get_repository(owner, repo_name)
            placeholder_comment = github_utils.post_comment(repository, pull_number, "Test analysis in progress...")

            updated_files, commit_messages = self.handle_pull_request(repository, pull_number, head_ref)
            existing_tests = self.get_existing_test_files(repository, head_ref)

            gating_result = self.gating_step(title, updated_files, commit_messages, existing_tests)
            if gating_result.shouldGenerateTests == False:
                github_utils.update_comment(placeholder_comment, f"Skipping test generation: {gating_result.reasoning}")
                return

            test_proposals = self.generate_test_cases(title, updated_files, commit_messages, existing_tests, gating_result.recommendations)
            self.commitTestChanges(repository, head_ref, test_proposals)
            self.update_comment_with_test_results(placeholder_comment, head_ref, test_proposals)
        except Exception as e:
            print("Error handling test PR:", e)

    def gating_step(self, title, updated_files, commit_messages, existing_tests):        
        response = generate_gating_response(title, updated_files, commit_messages, existing_tests)
        return response

    def generate_test_cases(self, title, updated_files, commit_messages, existing_tests, recommendations):
        response=generate_test_case_response(title, updated_files, commit_messages, existing_tests, recommendations)
        return response

    def commitTestChanges(self, repository, head_ref, new_test_proposals):
        for proposal in new_test_proposals.test_proposals:
            print(proposal)
            filename = proposal.filename
            test_content = proposal.testContent
            actions = proposal.actions
            for action in actions:
                if action.action == "create":
                    github_utils.create_file(repository,filename, f"Add tests: {filename}", test_content, head_ref)
                if action.action == "update":
                    file = repository.get_contents(filename, ref=head_ref)
                    github_utils.update_file(repository,filename, f"Update tests: {filename}", test_content, file.sha, head_ref)
                if action.action == "rename":
                    old_file=action.old_filename
                    file = repository.get_contents(old_file, ref=head_ref)
                    # Create the new file with the same content
                    github_utils.create_file(repository, filename, f"Renaming {old_file} to {filename}", test_content, head_ref)
                    # Delete the old file
                    github_utils.delete_file(repository, old_file, f"Removed old file {old_file} after renaming to {filename}", file.sha, head_ref)

    def update_comment_with_test_results(self, placeholder_comment, head_ref, new_test_proposals):
        test_list = "\n".join([f"- **{proposal.filename}**" for proposal in new_test_proposals.test_proposals])

        # Construct the comment body
        if new_test_proposals:
            body = f"""### AI Test Generator

    Added/updated these test files on branch `{head_ref}`:
    
    {test_list}

    *(Pull from that branch to see & modify them.)*
    """
        else:
            body = "### AI Test Generator\n\n No test proposals were generated."
        
        github_utils.update_comment(placeholder_comment, body)
    