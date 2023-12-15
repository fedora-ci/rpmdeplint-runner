import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

logger = logging.getLogger(__name__)


def http_get(url, as_json=False):
    """TODO."""
    retry_strategy = Retry(
        total=5,
        status_forcelist=[
            429,  # Too Many Requests
            500,  # Internal Server Error
            502,  # Bad Gateway
            503,  # Service Unavailable
            504,  # Gateway Timeout
        ],
        method_whitelist=["GET"],
        backoff_factor=2,  # wait 1, 2, 4, 8, ... seconds between retries
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    http = requests.Session()
    http.mount("https://", adapter)
    http.mount("http://", adapter)

    response = http.get(url)
    content = response.json() if as_json else response.content
    return content, response.status_code


def run_command(
    cmd: list[str],
    env=None,
    update_env=None,
    stdout=None,
    stderr=None,
    stdin=None,
    cwd: Optional[Path] = None,
    raise_on_error=False,
):
    """TODO."""
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
        preexec_fn=os.setsid,
    )
    logger.info(f"Running command {' '.join(cmd)}")
    stdout, stderr = proc.communicate()
    return_code = proc.returncode

    if not return_code and raise_on_error:
        raise subprocess.CalledProcessError(return_code, cmd, stderr)

    return stdout, stderr, return_code


def fix_arches(arches: list[str]) -> list[str]:
    if "noarch" not in arches:
        arches.append("noarch")
    return arches


def configure_logging_for_test(test_name: str, arch: str) -> None:
    """Redirect everything rpmdeplint has to say to a file.

    Only log messages though, not stdout/stderr.
    """
    logger = logging.getLogger("rpmdeplint")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    log_filename = f"{test_name}-{arch}.log"
    handler = logging.FileHandler(log_filename)
    handler.setFormatter(formatter)

    logger.addHandler(handler)


def run_rpmdeplint(
    test_name: str,
    repo_urls: dict[str, str],
    rpms: list[Path],
    arch: str,
    work_dir,  # TODO: unused
) -> int:
    """Run rpmdeplint."""
    repo_params = []
    for name, url in repo_urls.items():
        repo_params.extend(["--repo", f"{name},{url}"])

    # [Path] -> [str]
    rpms_list = [str(x) for x in rpms]

    args = ["--quiet", test_name, "--arch", arch, *repo_params, *rpms_list]

    configure_logging_for_test(test_name, arch)
    from rpmdeplint import cli as rpmdeplint_cli

    return rpmdeplint_cli.main(args)
