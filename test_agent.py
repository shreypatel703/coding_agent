import json
from base_agent import g, handlePullRequestBase
from github_auth import postPlaceholderComment, getFileContent, updateComment
from llm import generate_text, generate_json
import xml.etree.ElementTree as ET


def getExistingTestFiles(repository, ref, dirPath= "tests"):
    files = []
    try:
        contents = repository.get_contents(dirPath)
        for item in contents:
            if item.type == "file":
                content = getFileContent(repository, item.path, ref)
                files.append(content)
            elif item.type == "folder":
                files.extend(getExistingTestFiles(repository, ref, item.path))
    except Exception as ex:
        print("Error Getting existing test files: ", ex)
    return files
    
def gatingStep(title, updated_files, commit_messages, existing_test_files):
    existing_tests_str = {
        "Existing Tests": [{"File Name": f["filename"], "Content": f["content"]} for f in existing_test_files]
    }
    updated_files={
        "File Updates": [{"File Name": f["filename"], "Content": str(f["status"])+" (Excluded)"} if f["excluded"] else {"File Name": f["filename"], "Content": str(f["status"]), "Patch":f["patch"], "Content": f["content"]} for f in updated_files]
    }
    commit_messages_str = '\n'.join([f" - {msg}" for msg in commit_messages])
    print("c")
    try:
        body = f"""You are an expert in deciding if tests are needed for these changes.
You have the PR title, commits, and file diffs/content. Only return the object in JSON format: 
{{"decision":{{"shouldGenerateTests":'True' or 'False',"reasoning":"some text","recommendations":"some text"}}}}

Title: {title}
Commits:
{commit_messages_str}
Changed Files:
{json.dumps(updated_files)}
Existing Tests:
{json.dumps(existing_tests_str)}

Note: Do not include any text other than the JSON object itself. Output should not be a string. It should be a JSON object
"""
        text = generate_json(body)
        with open("xml.html", "w") as f:
            f.write(text)
        return json.loads(text)
    except Exception as error:
        print("Error generating or parsing AI analysis:", error)
        return {
            "summary": "We were unable to analyze the code due to an internal error.",
            "fileAnalyses": [],
            "overallSuggestions": []
        }

def parseTestsXml(text: str):
    try:
        print("a")
        text = text[text.find("<tests>"):text.find("</tests>")+len("</tests>")]
        root = ET.fromstring(text)
        print("b")
        tests = []
        for proposal in root.find("testProposals").findall("proposal"):
            print("c")

            filename = proposal.find("filename").text
            test_type = proposal.find("testType").text
            test_content = proposal.find("testContent").text.strip() if proposal.find("testContent") is not None else ""
            print("d")
            actions = []
            action_elements = proposal.find("actions")
            if action_elements is not None:
                print("e")
                for action in action_elements.findall("action"):
                    action_type = action.text
                    old_filename = action.find("oldFilename").text if action_type == "rename" else None
                    actions.append({"action": action_type, "oldFilename": old_filename})
                print("f")
            tests.append({
                "filename": filename,
                "testType": test_type,
                "testContent": test_content,
                "actions": actions
            })
        print(tests)
        return tests
    
    except Exception as ex:
        print("Error Parsing XML Tests")
        raise ex

def updateTests(title, updated_files, commit_messages, existing_test_files, recommendations):
    try:
        print("a")
        existing_tests_str = {
            "Existing Tests": [{"File Name": f["filename"], "Content": f["content"]} for f in existing_test_files]
        }
        print("b")
        updated_files={
            "File Updates": [{"File Name": f["filename"], "Content": str(f["status"])+" [Excluded]"} if f["excluded"] else {"File Name": f["filename"], "Content": str(f["status"]), "Patch":f["patch"], "Content": f["content"]} for f in updated_files]
        }
        print("c")
        commit_messages_str = '\n'.join([f" - {msg}" for msg in commit_messages])
        print("d")
        prompt = """
    You are an expert software developer specializing in writing tests for a Python codebase.

    You may use the recommendation below and/or go beyond it.

    Recommendation: {recommendations}

    Remember - you only generate tests for Python code. This includes things like functions, classes, modules, and scripts. You do not generate tests for front-end code such as JavaScript or UI components.

    Rules for naming test files:
    1) If a file contains a Python module, the test filename MUST follow the convention: "test_<module_name>.py".
    2) If the file being tested is inside a package, the test file should reside in the corresponding `tests/` directory, mirroring the structure of the source code.
    3) If an existing test file has the wrong name, propose renaming it.
    4) If updating an existing test file that has the correct name, update it in place.

    We have two test categories:
    (1) Unit tests (pytest/unittest) in `tests/unit/`
    (2) Integration tests in `tests/integration/`

    If an existing test already covers related functionality, prefer updating it rather than creating a new file. Return final content for each file you modify or create.

    Other rules:
    - Mock external dependencies and database calls where necessary.
    - Follow best practices for structuring test functions (given/when/then, AAA - Arrange, Act, Assert).
    - Use pytest fixtures where appropriate for reusable setup/teardown logic.

    Title: ${title}
    Commits:
    {commits}
    Changed Files:
    ${changedFilesPrompt}
    Existing Tests:
    ${existingTestsPrompt}

    Return ONLY valid XML in the following structure:
    <tests>
    <testProposals>
        <proposal>
        <filename>tests/unit/test_<module_name>.py</filename>
        <testType>unit or integration</testType>
        <testContent><![CDATA[
    YOUR TEST CODE HERE
    ]]></testContent>
        <actions>
            <action>create</action> OR <action>update</action> OR <action>rename</action>
            <!-- if rename -->
            <oldFilename>tests/unit/old_test_name.py</oldFilename>
        </actions>
        </proposal>
    </testProposals>
    </tests>

    ONLY return the <tests> XML with proposals. Do not add extra commentary.
    """.format(recommendations=recommendations, title=title, commits=commit_messages_str, changedFilesPrompt=json.dumps(updated_files), existingTestsPrompt=json.dumps(existing_tests_str))
        text = generate_text(prompt)
        with open("tests.html", "w") as f:
            f.write(text)
        return parseTestsXml(text)
    except Exception as error:
        print("Error generating or parsing AI analysis:", error)
        return []

def commitTestChanges(repository, headRef, new_test_proposals):
    for proposal in new_test_proposals:
        filename = proposal["filename"]
        test_type = proposal["testType"]
        test_content = proposal["testContent"]
        actions = proposal["actions"]
        for action in actions:
            if action["action"] == "create":
                repository.create_file(filename, f"Add tests: {filename}", test_content, branch=headRef)
            if action["action"] == "update":
                repository.update_file(filename, f"Update tests: {filename}", test_content, branch=headRef)
            if action["action"] == "rename":
                old_file=action["old_filename"]
                file = repository.get_contents(old_file, ref=headRef)
                # Create the new file with the same content
                repository.create_file(filename, f"Renaming {old_file} to {filename}", test_content, branch=headRef)

                # Delete the old file
                repository.delete_file(old_file, f"Removed old file {old_file} after renaming to {filename}", file.sha, branch=headRef)






def updateCommentWithTestResults(placeholder_comment, headRef, new_test_proposals):
    test_list = "\n".join([f"- **{t['filename']}**" for t in new_test_proposals])

    # Construct the comment body
    if new_test_proposals:
        body = f"""### AI Test Generator

Added/updated these test files on branch `{headRef}`:
{test_list}

*(Pull from that branch to see & modify them.)*
"""
    else:
        body = "### AI Test Generator\n\n⚠️ No test proposals were generated."
    
    updateComment(placeholder_comment, body)

def handlePullRequestForTestAgent(payload):
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    pullNumber = payload["pull_request"]["number"]
    title = payload["pull_request"]["title"]
    headRef = payload["pull_request"]["head"]["ref"]
    
    try:
        repository = g.get_repo(f"{owner}/{repo}")

        placeholder_comment = postPlaceholderComment(repository, pullNumber, "AI Test Generation in progress...")
        
        updated_files, commit_messages = handlePullRequestBase(repository, pullNumber, headRef)

        existing_test_files = getExistingTestFiles(repository, headRef)
        with open("existing_tests.json", "w") as f:
            json.dump({
                "Files": existing_test_files
            }, f, indent=4)
        gating_result = gatingStep(title, updated_files, commit_messages, existing_test_files)
        with open("gating.json", "w") as f:
            json.dump(gating_result, f, indent=4)
        if gating_result["decision"]["shouldGenerateTests"] != "True":
            print("skipping")
            updateComment(placeholder_comment, f"Skipping test generation: {gating_result['reasoning']}")
            return
        print("Hello")
        new_test_proposals = updateTests(title, updated_files, commit_messages, existing_test_files, gating_result["decision"]["recommendations"])
        with open("new_tests.json", "w") as f:
            json.dump({
                "tests": new_test_proposals
            }, f, indent=4)
        # with open("new_tests.json", "w") as f:
        #     new_test_proposals = json.load(f)["tests"]
        if len(new_test_proposals) > 0:
            commitTestChanges(repository, headRef, new_test_proposals)

        updateCommentWithTestResults(placeholder_comment, headRef, new_test_proposals)


        print(f"Submitted code review for PR #${pullNumber} in ${owner}/${repo}")
    except Exception as e:
        print(e)
        return -1