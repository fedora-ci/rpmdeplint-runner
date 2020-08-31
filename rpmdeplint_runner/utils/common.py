import logging
import os
import pathlib
import requests
import subprocess
import time
import xml.etree.cElementTree as ET

from xml.dom import minidom

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


logger = logging.getLogger(__name__)


def http_get(url, as_json=False):
    """TODO.
    """
    retry_strategy = Retry(
        total=5,
        status_forcelist=[
            429,  # Too Many Requests
            500,  # Internal Server Error
            502,  # Bad Gateway
            503,  # Service Unavailable
            504   # Gateway Timeout
        ],
        method_whitelist=["GET"],
        backoff_factor=2  # wait 1, 2, 4, 8, ... seconds between retries
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    http = requests.Session()
    http.mount("https://", adapter)
    http.mount("http://", adapter)

    response = http.get(url)
    content = response.content
    if as_json:
        content = response.json()
    return content, response.status_code


def run_command(
    cmd, timeout=None, env=None, update_env=None,
    stdout=None, stderr=None, stdin=None, cwd=None,
    raise_on_error=False
):
    """TODO.
    """
    if update_env:
        env = env if env is not None else os.environ.copy()
        env.update(update_env)

    proc = subprocess.Popen(
        cmd,
        env=env,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        universal_newlines=True,
        bufsize=0,
        cwd=cwd,
        preexec_fn=os.setsid
    )
    logger.info('Running command "{cmd}"'.format(cmd=' '.join(cmd)))
    stdout, stderr = proc.communicate()
    return_code = proc.returncode

    if not return_code and raise_on_error:
        raise subprocess.CalledProcessError(return_code, cmd, stderr)

    return stdout, stderr, return_code


def fix_arches(arches):
    if 'x86_64' in arches and 'i686' not in arches:
        arches.append('i686')
    if 'noarch' not in arches:
        arches.append('noarch')
    return arches


def run_rpmdeplint(test_name, repo_urls, rpms_list, arch, work_dir):
    repo_params = []
    for name, url in repo_urls.items():
        repo_params.extend(['--repo', '{name},{url}'.format(name=name, url=url)])

    # pathlib.Path -> str
    rpms_list = [str(x) for x in rpms_list]

    cmd = ['rpmdeplint', '--quiet', test_name, '--arch', arch]

    # FIXME: this should be configurable from the outside (from fmf file(?)), and not hardcoded here
    if test_name == 'check-conflicts':
        # See: bugzilla.redhat.com/show_bug.chi?id=1862350
        cmd.extend(['--skip-filename', '/usr/lib/.build-id.*', '--skip-filename', '/usr/lib/debug/.build-id.*'])
    cmd.extend(repo_params)
    cmd.extend(rpms_list)

    stdout, stderr, return_code = run_command(cmd, cwd=work_dir)

    return stdout, return_code
