#!/bin/python3
# -*- coding: utf-8 -*-
# Copyright 2020, Red Hat, Inc.
# License: GPL-2.0+ <http://spdx.org/licenses/GPL-2.0+>

"""
run rpmdeplint tool for specific koji tasks
"""
import argparse
import subprocess
import re
import json
import glob
import os
import sys
import time
import traceback
import requests
import koji
import yaml


TEST_PASS = 0
TEST_FAIL = 1
TEST_SKIP = 2

RESULTS = {'results': []}

def _run(cmd, logfile=None):
    sys.stdout.flush()
    sys.stderr.flush()
    print("INFO: Running: '{0}'...".format(cmd))
    sp = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    # Flush stdout before command completes
    stdout = b""
    while sp.poll() is None:
        new_data = sp.stdout.readline()
        stdout += new_data
        new_str = new_data.decode('ascii', 'ignore')
        sys.stdout.write(new_str)
        sys.stdout.flush()
        # Just print any stderr messages, don't save it to logifle
        sys.stderr.flush()
        if logfile and new_data:
            with open(logfile, 'a') as _file:
                _file.write('{0}'.format(new_str))

    #stdout, stderr = p.communicate()
    #sys.stdout.flush()
    #sys.stderr.flush()

    return sp.returncode

def _query_url(url, retry=10):
    exception = None
    while retry > 0:
        try:
            resp = requests.get(url, verify=False)
        except Exception as e:
            exception = e
            retry -= 1
            time.sleep(1)
            continue
        if resp.status_code < 200 or resp.status_code >= 300:
            return None
        return resp.text
    _print_log("FAIL: Could not connect to {0}".format(url), "console.log")
    _print_log("Exception: %s" % exception, "console.log")
    return None

def _print_log(msg, logfile=None):
    print(msg)
    if logfile:
        with open(logfile, "a") as myfile:
            myfile.write(msg + "\n")


def _download_builds(arch, build):
    arch_options = "--arch {0} --arch noarch".format(arch)
    if arch == "x86_64":
        arch_options += " --arch i686"
    print("INFO: Dowloading packages for build: {0}...".format(build['nvr']))
    if _run("koji download-build {0} --noprogress --debuginfo --task-id {1}".format(arch_options, build['task_id']), "koji.log") != 0:
        print("INFO: Could not download build for {0}".format(arch))
        return False
    return True


def prepare_rpms(arch, builds):
    success = True
    for build in builds:
        # download rpms
        if not _download_builds(arch, build):
            # Dont report error if there is no build for this arch
            continue

    return success

def _add_test_results(testcase, test_result, test_log_filename):
    test_result_str = "fail"
    if test_result == TEST_PASS:
        test_result_str = "pass"

    # Rename log file to contain status as prefix
    updated_filename = "{}-{}".format(test_result_str.upper(), test_log_filename)
    os.rename(test_log_filename, updated_filename)

    result = {}
    result['test'] = testcase
    result['result'] = test_result_str
    result['logs'] = [updated_filename]
    RESULTS["results"].append(result)

    return True


def run_rpmdeplint(testcase, repos, arch, test_log_name):
    rpms = glob.glob("*.rpm")
    if not rpms:
        return

    rpms = " ".join(rpms)

    repo_param = ""
    for repo in repos:
        repo_param += "--repo {0} ".format(repo)

    test_log_filename = "{}.log".format(test_log_name)

    # set pipefail so we exit with rpmdeplint error if it fails
    cmd = "set -o pipefail; rpmdeplint {0} {1} --arch={2} {3} |& tee {4}".format(testcase, repo_param, arch, rpms, test_log_filename)
    test_result = _run(cmd, "console.log")
    testcase_name = "{0}-{1}".format(arch, testcase)
    if not _add_test_results(testcase_name, test_result, test_log_filename):
        _print_log("FAILURE Can't add result {0} from {1} to results".format(test_result, testcase_name), "console.log")



def _run_test(repos, arch):
    repo_params = ""
    repo_file_log = "repos.log"
    for repo in repos:
        repo_params += " -r {0}".format(repo)
        splitted_repo = repo.split(",")
        if os.path.isfile(repo_file_log) and (_run("grep '{0}' {1}".format(splitted_repo[1], repo_file_log)) != 0):
            _run("echo {0} >> {1}".format(splitted_repo[1], repo_file_log))

    testcases = ["check-sat", "check-repoclosure", "check-conflicts", "check-upgrade"]

    for test in testcases:
        test_log_name = "{0}-{1}".format(arch, test)
        run_rpmdeplint(test, repos, arch, test_log_name)


def main():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument("--task-id", "-t", dest="task_id", required=True,
                        action="append", type=str, help="A comma-separated list of Koji task IDs")
    parser.add_argument("--release", "-r", dest="release", required=True,
                        help="release, like f31")
    args = parser.parse_args()

    koji_hub = koji.ClientSession("https://koji.fedoraproject.org/kojihub")

    version = None
    # in most cases fed_version is equal to version, but when rawhide it should be actually the Fedora number of rawhide
    fed_version = None

    m = re.match(r"^f(\d+)$", args.release)
    if not m:
        _print_log("FAIL: invalid Fedora release {0}".format(args.release))
        sys.exit(1)
    fed_version = m.group(1)
    version = m.group(1)


    # not using http://download.fedoraproject.org/pub/fedora/linux/ because it redirect to mirrors
    # and this could cause some issues of missing releases, specially for branched versions
    base_repo_url = "https://kojipkgs.fedoraproject.org/compose/{0}/latest-Fedora-{0}/compose/Everything".format(version)

    # need to query release to check if it is rawhide or not
    output = _query_url("https://bodhi.fedoraproject.org/releases/?state=pending")
    if not output:
        _print_log("FAIL: Could not query bodhi", "console.log")
        sys.exit(1)
    fedora_releases = json.loads(output)
    for release in fedora_releases['releases']:
        if release["version"] == fed_version:
            # Check if release got branched, but not released yet...
            base_repo_url = "https://kojipkgs.fedoraproject.org/compose/branched/latest-Fedora-{0}/compose/Everything".format(version)
            if not _query_url(base_repo_url):
                base_repo_url = "https://kojipkgs.fedoraproject.org/compose/rawhide/latest-Fedora-Rawhide/compose/Everything"
                version = "rawhide"
            break

    base_koji_repo_url = "https://kojipkgs.fedoraproject.org/repos/f{0}-build/latest".format(fed_version)

    builds = []
    for task_id_str in args.task_id:
        task_id_list = [int(x) for x in task_id_str.strip().split(',')]
        for task_id  in task_id_list:
            task_builds = koji_hub.listBuilds(taskID=task_id)
            if task_builds:
                builds.extend(task_builds)

    if not builds:
        _print_log("FAIL: Could not get build", "console.log")
        sys.exit(1)


    supported_archs = ["x86_64", "aarch64", "armhfp"]

    infra_failure = False
    ran_at_least_once = False

    for arch in supported_archs:
        release_repo = "Fedora-{0}-repo,{1}/{2}/os".format(version, base_repo_url, arch)
        latest_koji_repo = "koji-f{0}-repo,{1}/{2}".format(fed_version, base_koji_repo_url, arch)
        dep_repos = [release_repo, latest_koji_repo]

        _run("rm -rf *.rpm")

        if not prepare_rpms(arch, builds):
            infra_failure = True
            continue

        if not glob.glob("*.rpm"):
            # in case there is no build for this arch, just continue
            continue

        _run_test(dep_repos, arch)

        ran_at_least_once = True

    if not ran_at_least_once:
        # We could run test for any arch
        infra_failure = True
        _print_log("FAILURE could not run test for any arch", "console.log")

    _run("rm -rf *.rpm")
    with open('results.yml', 'w') as yml:
        yaml.dump(RESULTS, yml)

    if infra_failure:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        _print_log(traceback.format_exc(), "console.log")
        sys.exit(1)
