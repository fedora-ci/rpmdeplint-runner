#!/bin/python3

import argparse
import sys
import requests
import logging

from rpmdeplint_runner.outcome import TmtExitCodes, RpmdeplintCodes
from rpmdeplint_runner.utils import run_rpmdeplint
from rpmdeplint_runner.utils.fedora import download_rpms, get_repo_urls, get_cached_rpms, is_prepared


logger = logging.getLogger(__name__)


def parse_args():
    """Parse arguments."""
    parser = argparse.ArgumentParser(description='Run rpmdeplint tests')

    subparsers = parser.add_subparsers(title="commands", dest="command")
    prepare_parser = subparsers.add_parser('prepare', help='prepare given workdir for running tests')
    prepare_parser.add_argument(
        "--task-id", "-t", dest="task_id", required=True,
        action="append", type=str, help="a comma-separated list of Koji task IDs"
    )
    prepare_parser.add_argument(
        "--release", "-r", dest="release_id", required=True, help="release id, e.g.: f33"
    )
    prepare_parser.add_argument(
        "--arch", dest="arch", required=True, action="append", type=str,
        help="a comma-separated list of repository architectures"
    )
    prepare_parser.add_argument(
        "--os", dest="os", required=False, default='fedora', choices=['fedora'],
        help="operating system, e.g.: fedora"
    )
    prepare_parser.add_argument(
        "--workdir", dest="work_dir", required=True,
        help="workdir where to store files"
    )

    test_parser = subparsers.add_parser('run-test', help='run the given rpmdeplint test', parents=[prepare_parser], add_help=False)
    test_parser.add_argument(
        "--name", "-n", dest="test_name", required=True, choices=['check', 'check-sat', 'check-repoclosure', 'check-conflicts', 'check-upgrade'],
        help="rpmdeplint test name"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # turn string (a comma-separated list of task ids) into a Python list
    # "428432,4535432" -> ["428432", "4535432"]
    task_ids = []
    for task_id_str in args.task_id:
        task_ids.extend([int(x) for x in task_id_str.strip().split(',')])
    args.task_id = task_ids

    # turn string (a comma-separated list of arches) into a Python list
    # "x86_64,i686" -> ["x86_64", "i686"]
    arches = []
    for arch_str in args.arch:
        arches.extend([x for x in arch_str.strip().split(',')])
    args.arch = arches

    return args


def prepare(work_dir, task_ids, arches):
    """Run prepare command.
    
    :param work_dir: str, workdir
    :param task_ids: list, task ids
    :param arches: list, architectures
    :return: None
    """
    for task_id in task_ids:
        download_rpms(task_id, work_dir, arches)


def run_test(work_dir, test_name, release_id, os, task_ids=None, arch=None):
    """Run rpmdeplint test.

    :param work_dir: str, workdir
    :param test_name: str, name of the rpmdeplint test to run
    :param release_id: str, release id, example: f33
    :param task_ids: list, task ids
    :param arch: str, architecture
    :return: None
    """
    repo_urls = get_repo_urls(release_id, arch)
    rpms_list = get_cached_rpms(work_dir, [arch], task_ids)

    if not is_prepared(work_dir, task_ids, [arch]):
        # TODO: stderr
        print(
            'Error: unable to run the "{test_name}({arch})" test as RPMs for the task id {task_id} were not downloaded.'.format(
                test_name=test_name, task_id=str(task_ids), arch=arch
            )
        )
        sys.exit(TmtExitCodes.ERROR.value)

    if not rpms_list:
        # skip the test if there are no RPMs for given arch
        # TODO: stderr
        print(
            'Skipping "{test_name}({arch})" test for the task id {task_id} as there are no RPMs for that architecture...'.format(
                test_name=test_name, task_id=str(task_ids), arch=arch
            )
        )
        sys.exit(TmtExitCodes.SKIPPED.value)

    return_code = run_rpmdeplint(test_name, repo_urls, rpms_list, arch, work_dir)
    # fail if rpmdeplint failed
    sys.exit(TmtExitCodes.from_rpmdeplint(RpmdeplintCodes.from_rc(return_code)).value)


def run(args):
    """Run, Rpmdeplint, run!"""
    if args.command == 'prepare':
        prepare(args.work_dir, args.task_id, args.arch)
    elif args.command == 'run-test':
        arch = args.arch[0]
        run_test(args.work_dir, args.test_name, args.release_id, args.os, args.task_id, arch)


if __name__ == '__main__':
    args = parse_args()
    run(args)
