#!/usr/bin/python3

import argparse
import logging
import sys
import yaml
from os import getenv
from pathlib import Path
from typing import Optional

from rpmdeplint_runner.outcome import RpmdeplintCodes, TmtExitCodes, TmtResult
from rpmdeplint_runner.utils import run_rpmdeplint
from rpmdeplint_runner.utils.fedora import (
    download_rpms,
    get_repo_urls,
    get_cached_rpms,
    is_prepared,
)

logger = logging.getLogger(__name__)


def parse_args():
    """Parse arguments."""
    parser = argparse.ArgumentParser(description="Run rpmdeplint tests")

    subparsers = parser.add_subparsers(title="commands", dest="command")
    prepare_parser = subparsers.add_parser(
        "prepare", help="prepare given workdir for running tests"
    )
    prepare_parser.add_argument(
        "--task-id",
        "-t",
        dest="task_id",
        required=True,
        action="append",
        type=str,
        help="a comma-separated list of Koji task IDs",
    )
    prepare_parser.add_argument(
        "--release",
        "-r",
        dest="release_id",
        required=True,
        help="release id, e.g.: f33",
    )
    prepare_parser.add_argument(
        "--arch",
        dest="arch",
        required=True,
        action="append",
        type=str,
        help="a comma-separated list of repository architectures",
    )
    prepare_parser.add_argument(
        "--workdir", dest="work_dir", help="workdir where to store files"
    )

    test_parser = subparsers.add_parser(
        "run-test",
        help="run the given rpmdeplint test",
        parents=[prepare_parser],
        add_help=False,
    )
    test_parser.add_argument(
        "--name",
        "-n",
        dest="test_name",
        required=True,
        choices=[
            "check",
            "check-sat",
            "check-repoclosure",
            "check-conflicts",
            "check-upgrade",
        ],
        help="rpmdeplint test name",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # turn string (a comma-separated list of task ids) into a Python list
    # ["428432,4535432", "123456"] -> ["428432", "4535432", "123456"]
    task_ids = []
    for task_id_str in args.task_id:
        task_ids.extend(list(task_id_str.strip().split(",")))
    args.task_id = task_ids

    # turn string (a comma-separated list of arches) into a Python list
    # "x86_64,i686" -> ["x86_64", "i686"]
    arches = []
    for arch_str in args.arch:
        arches.extend(list(arch_str.strip().split(",")))
    args.arch = arches

    args.work_dir = Path(args.work_dir) if args.work_dir else Path.cwd()

    return args


def prepare(work_dir: Path, task_ids: list[str], arches: list[str]) -> None:
    """Run prepare command.

    :param work_dir: workdir
    :param task_ids: task ids
    :param arches: list of architectures
    :return: None
    """
    for task_id in task_ids:
        download_rpms(task_id, work_dir, arches)


def run_test(
    work_dir: Path,
    test_name: str,
    release_id: str,
    task_ids: list[str],
    arch: str,
) -> None:
    """Run rpmdeplint test.

    :param work_dir: workdir
    :param test_name: name of the rpmdeplint test to run
    :param release_id: release id, example: f33
    :param task_ids: task ids
    :param arch: architecture
    :return: None
    """
    repo_urls = get_repo_urls(release_id, arch)
    rpms_list = get_cached_rpms(work_dir, [arch], task_ids)

    if not is_prepared(work_dir, task_ids, [arch]):
        # TODO: stderr
        print(
            f'Error: unable to run the "{test_name}({arch})" test '
            f"as RPMs for the task id {task_ids} were not downloaded."
        )
        save_results_and_exit(TmtExitCodes.ERROR)

    if not rpms_list:
        # skip the test if there are no RPMs for given arch
        # TODO: stderr
        print(
            f'Skipping "{test_name}({arch})" test for the task id {task_ids} '
            f"as there are no RPMs for that architecture..."
        )
        save_results_and_exit(TmtExitCodes.SKIPPED)

    return_code = run_rpmdeplint(test_name, repo_urls, rpms_list, arch, work_dir)
    tmt_exit_code = TmtExitCodes.from_rpmdeplint(RpmdeplintCodes.from_rc(return_code))
    save_results_and_exit(
        tmt_exit_code,
        f"{test_name}-{arch}.log",
    )


def save_results_and_exit(
    tmt_exit_code: TmtExitCodes, log_name: Optional[str] = None
) -> None:
    if getenv("TMT_TEST_DATA"):
        results = [
            {
                "name": "/rpmdeplint",
                "result": TmtResult.from_exit_code(tmt_exit_code).value,
                "log": ["../output.txt", log_name] if log_name else ["../output.txt"],
            }
        ]
        with open(f"{getenv('TMT_TEST_DATA')}/results.yaml", "w") as file:
            yaml.dump(results, file)
        sys.exit(0)

    sys.exit(tmt_exit_code.value)


def run(args):
    """Run, Rpmdeplint, run!"""
    if args.command == "prepare":
        prepare(args.work_dir, args.task_id, args.arch)
    elif args.command == "run-test":
        arch = args.arch[0]
        run_test(args.work_dir, args.test_name, args.release_id, args.task_id, arch)


if __name__ == "__main__":
    args = parse_args()
    run(args)
