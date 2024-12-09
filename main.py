import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass

import click
import requests

TOKEN = os.getenv("CODE_SMASH_TOKEN", "072025bd6475721c42b34c13bda4430ad6130551")
BASE_API_URL = os.getenv("CODE_SMASH_BASE_API_URL", "https://code-smash.com")

logger = logging.getLogger(__name__)


class CodeSmashCLIException(Exception):
    pass


class CodeSmashAPIException(Exception):
    pass


@dataclass
class AIFeedback:
    issue_solved: bool
    feedback: str


@dataclass
class DiffFeedback:
    hash: str
    subtask: int
    feedback: AIFeedback | None

    @classmethod
    def from_dict(cls, d: dict) -> "DiffFeedback":
        feedback = d.pop("feedback", None)
        if feedback is not None and isinstance(feedback, dict):
            feedback_obj = AIFeedback(**feedback)
        else:
            feedback_obj = None
        return cls(feedback=feedback_obj, **d)


class CodeSmashAPIHandler:
    def __init__(self, token: str, base_url: str):
        self._token = token
        self._base_url = base_url

    def _request(self, method: str, path: str, data: dict | None = None) -> dict:
        headers = {"Authorization": f"Token {self._token}"}
        response = requests.request(
            method,
            url=f"{self._base_url}{path}",
            headers=headers,
            json=data,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError:
            raise CodeSmashAPIException(f"Failed to make request to {path} with: {response.text}")
        return response.json()

    def get_diff_feedback(self, hash: str, diff: str, subtask_id: int) -> DiffFeedback:
        data = self._request(
            method="POST",
            path="/api/smash/diff",
            data={"hash": hash, "diff": diff, "subtask": subtask_id},
        )
        return DiffFeedback.from_dict(data)

    def get_subtask(self, subtask_id: int) -> dict:
        data = self._request(
            method="GET",
            path=f"/api/smash/groups/user/substask/{subtask_id}",
        )
        return data


class CodeSmashCLIHandler:
    def __init__(self, project_path: str, main_branch_name: str):
        self._project_path = project_path
        self._main_branch_name = main_branch_name
        self._instance_has_been_validated = False

        self._code_smash_api_client = CodeSmashAPIHandler(
            token=TOKEN,
            base_url=BASE_API_URL,
        )

    def validate_instance(self):
        try:
            self._validate_project_path(self._project_path)
            self._validate_main_branch_name(self._main_branch_name)
        except Exception as e:
            logger.error(e)
            return
        self._instance_has_been_validated = True

    def _validate_main_branch_name(self, branch_name: str) -> bool:
        branches = self._get_branches()
        cleared = [b.lstrip("*").strip() for b in branches if b]
        main_branch_exists = branch_name in cleared
        if not main_branch_exists:
            raise CodeSmashCLIException(f"Main branch {branch_name} does not exist.")
        return True

    @staticmethod
    def _validate_project_path(path: str) -> bool:
        path_exist = os.path.exists(path)
        if not path_exist:
            raise CodeSmashCLIException(f"Given Path {path} does not exist.")
        is_dir = os.path.isdir(path)
        if not is_dir:
            raise CodeSmashCLIException(f"Given Path {path} is not a directory.")
        git_dir = os.path.join(path, ".git")
        git_dir_exist = os.path.exists(git_dir)
        if not git_dir_exist:
            raise CodeSmashCLIException(f"Given Path {path} is not a git repository.")
        return True

    def _get_branches(self) -> list[str]:
        cmd = ["git", "-C", self._project_path, "branch"]
        branches = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            text=True,
        )
        return branches.stdout.split("\n")

    def _get_current_branch_name(self) -> str:
        cmd = ["git", "-C", self._project_path, "branch", "--show-current"]
        branch = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            text=True,
        )
        return branch.stdout.strip()

    def _get_diff(self, ref_branch_name: str, branch_name: str) -> str:
        cmd = ["git", "-C", self._project_path, "diff", ref_branch_name, branch_name]

        logger.info(f'cmd {" ".join(cmd)}')

        diff = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            text=True,
        )
        return diff.stdout

    @staticmethod
    def _validate_branch_name(branch_name: str) -> bool:
        # branch must be in the format of `feat/code-smash/{{task_id}}`
        branch_name_is_valid = bool(re.match(r"feat/code-smash/\d+", branch_name))
        if not branch_name_is_valid:
            raise CodeSmashCLIException(f"Branch name {branch_name} is not valid.")
        return True

    @staticmethod
    def _get_subtask_id_from_branch_name(branch_name: str) -> int:
        return int(branch_name.split("/")[-1])

    def _get_current_hash(self) -> str:
        cmd = ["git", "-C", self._project_path, "rev-parse", "HEAD"]
        hash = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            text=True,
        )
        return hash.stdout.strip()

    def _fmt_feedback(self, diff: DiffFeedback) -> str:
        if diff.feedback is None:
            return "No feedback available."
        feedback_data = json.loads(diff.feedback.feedback)
        implementation_feedback = feedback_data.get("implementation", "")
        code_quality_feedback = feedback_data.get("code_quality", "")
        best_practices_feedback = feedback_data.get("best_practices", "")

        return (
            "Implementation:\n"
            f"{implementation_feedback}"
            "\n\n---\n"
            "Code Quality:\n"
            f"{code_quality_feedback}"
            "\n\n---\n"
            "Best Practices:\n"
            f"{best_practices_feedback}"
            "\n\n---\n"
            "Task is Fulfilled: "
            f"{'Yes. Code can be merged.' if diff.feedback.issue_solved else 'No.'}"
        )

    def get_code_feedback(self) -> str | None:
        if not self._instance_has_been_validated:
            logger.error("Instance has not been validated which is required for this operation.")
            return None

        try:
            current_branch = self._get_current_branch_name()
            self._validate_branch_name(current_branch)

            subtask_id = self._get_subtask_id_from_branch_name(current_branch)
            # just for subtask validation
            self._code_smash_api_client.get_subtask(subtask_id)

            current_hash = self._get_current_hash()
            diff = self._get_diff(ref_branch_name=self._main_branch_name, branch_name=current_hash)
            feedback = self._code_smash_api_client.get_diff_feedback(
                hash=current_hash,
                subtask_id=subtask_id,
                diff=diff,
            )
        except (CodeSmashAPIException, CodeSmashCLIException) as e:
            logger.error(e)
            return None
        return self._fmt_feedback(feedback)


@click.group("code-smash")
@click.pass_context
def cli(ctx: click.Context):
    pass


@cli.group("task")
def task():
    pass


@task.command("apply")
@click.option(
    "--local-path",
    required=True,
    type=str,
    help="Local path to project base directory.",
)
@click.option(
    "--main-branch-name",
    required=True,
    type=str,
    help="Name of main branch which is used (i.e. master, main).",
)
def apply(local_path: str, main_branch_name: str):
    handler = CodeSmashCLIHandler(project_path=local_path, main_branch_name=main_branch_name)
    handler.validate_instance()
    print(handler.get_code_feedback())


if __name__ == "__main__":
    cli()
