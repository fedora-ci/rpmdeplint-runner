import re
from pathlib import Path
from typing import Optional

from rpmdeplint_runner.utils import http_get, run_command, fix_arches

BUILDROOT_REPO_URL_TEMPLATE = (
    "https://kojipkgs.fedoraproject.org/repos/f{version}-build/{repo_id}/{arch}/"
)

REPO_URL_TEMPLATE = "https://kojipkgs.fedoraproject.org/compose/{state}/latest-Fedora-{version}/compose/Everything/{arch}/os/"
DEBUGINFO_REPO_URL_TEMPLATE = "https://kojipkgs.fedoraproject.org/compose/{state}/latest-Fedora-{version}/compose/Everything/{arch}/debug/tree/"

RAWHIDE_REPO_URL = "https://kojipkgs.fedoraproject.org/compose/rawhide/latest-Fedora-Rawhide/compose/Everything/{arch}/os/"
RAWHIDE_DEBUGINFO_REPO_URL = "https://kojipkgs.fedoraproject.org/compose/rawhide/latest-Fedora-Rawhide/compose/Everything/{arch}/debug/tree/"

BODHI_RELEASES_URL = "https://bodhi.fedoraproject.org/releases/"

KOJI_HUB_URL = "https://koji.fedoraproject.org/kojihub"
KOJI_TOP_URL = "https://kojipkgs.fedoraproject.org"


def get_repo_urls(
    release_id: str, arch: str, exclude_buildroot=False, exclude_debuginfo=False
) -> dict[str, str]:
    """Get repo URLs for given release id.

    :param release_id: release id, example: f40
    :param arch: architecture
    :param exclude_buildroot: bool, exclude buildroot repos or not
    :param exclude_debuginfo: bool, exclude debuginfo repos or not
    :return: dict, a dict where keys are repo names and values are repo URLs
    """

    version = get_version(release_id)
    repo_name = f"fedora-{version}-{arch}"
    debug_repo_name = f"fedora-debuginfo-{version}-{arch}"
    repo_url = RAWHIDE_REPO_URL.format(arch=arch)
    debug_repo_url = RAWHIDE_DEBUGINFO_REPO_URL.format(version=version, arch=arch)
    releases = get_releases_from_bodhi()

    if not is_rawhide(version, releases):
        if is_current(version, releases):
            state = version
            repo_url = REPO_URL_TEMPLATE.format(state=state, version=version, arch=arch)
            debug_repo_url = DEBUGINFO_REPO_URL_TEMPLATE.format(
                state=state, version=version, arch=arch
            )
        else:
            state = "branched"
            repo_url = REPO_URL_TEMPLATE.format(state=state, version=version, arch=arch)
            debug_repo_url = DEBUGINFO_REPO_URL_TEMPLATE.format(
                state=state, version=version, arch=arch
            )

            # we need to check that this pre-release repo already exists
            if not repo_exists(repo_url):
                # there are 2 cases when the repo URL will not exist:
                # the version is too old and the repo is simply
                # no longer available, or it is too soon after
                # branching and thus the repo is not available yet.
                # if this is tha latter, we simply fall back to rawhide repo.
                if not is_pending(version, releases):
                    raise ValueError(
                        f'Repo for release "{release_id}" doesn\'t exist: {repo_url}'
                    )
                # it's too early after branching — let's use Rawhide repo instead
                repo_url = RAWHIDE_REPO_URL.format(arch=arch)
                debug_repo_url = RAWHIDE_DEBUGINFO_REPO_URL.format(
                    version=version, arch=arch
                )

    result = {repo_name: repo_url}
    if not exclude_debuginfo:
        result[debug_repo_name] = debug_repo_url

    if not exclude_buildroot:
        buildroot_repo_name = f"fedora-buildroot-{version}-{arch}"
        buildroot_repo_url = BUILDROOT_REPO_URL_TEMPLATE.format(
            version=version, repo_id="latest", arch=arch
        )
        # there should be a file called "repo.json" in the repository directory; we fetch the file and extract
        # the real repository id from it. That way we don't have to rely on the ever-changing "latest" identifier
        # that could cause trouble during testing.
        repo_json_url = (
            buildroot_repo_url[: buildroot_repo_url.rfind(f"{arch}/")] + "repo.json"
        )
        response, _ = http_get(repo_json_url, as_json=True)
        if response and response.get("id"):
            buildroot_repo_url = BUILDROOT_REPO_URL_TEMPLATE.format(
                version=version, repo_id=response.get("id"), arch=arch
            )
        result[buildroot_repo_name] = buildroot_repo_url

    return result


def repo_exists(repo_url: str) -> bool:
    """Check if given repository exists.

    :param repo_url: repository URL
    :return: True if the repo exists, False otherwise
    """
    _, status = http_get(repo_url)
    return status != 404


def is_pending(version: str, releases: list[dict]) -> bool:
    """Check if given version is pending (is not released yet) or not.

    :param version: version
    :param releases: a list with information about fedora releases from Bodhi
    :return: True if given version is a pending release, False otherwise
    """
    return any(
        (
            release["version"] == version
            and release["id_prefix"] == "FEDORA"
            and release["state"] == "pending"
        )
        for release in releases
    )


def is_current(version: str, releases: list[dict]) -> bool:
    """Check if given version is "current" (released and supported) or not.

    :param version: version
    :param releases: a list with information about fedora releases from Bodhi
    :return: True if given version is a current release, False otherwise
    """
    return any(
        (
            release["version"] == version
            and release["id_prefix"] == "FEDORA"
            and release["state"] == "current"
        )
        for release in releases
    )


def get_version(release_id: str) -> str:
    """Get version from release id.

    :param release_id: release id, example: f40
    :return: version ("f40" -> "40")
    """
    if m := re.match(r"^f(\d+)$", release_id):
        return m[1]
    else:
        raise ValueError("Invalid release id: %s", release_id)


def is_rawhide(version: str, releases: list[dict]) -> bool:
    """Checks if given version is Rawhide or not.

    :param version: fedora version, e.g. "40"
    :param releases: a list with information about fedora releases from Bodhi
    :return: True if given version is Rawhide, False otherwise
    """
    # build a list of sorted pending versions; the last item in the list is Rawhide
    if pending_versions := sorted(
        {
            x["version"]
            for x in releases
            if x["id_prefix"] == "FEDORA"
            and x["state"] == "pending"
            and x["version"].isdigit()
        }
    ):
        return version == pending_versions[-1]
    else:
        raise ValueError("Unable to obtain a list of pending Fedora versions")


def get_releases_from_bodhi(state: Optional[str] = None) -> list[dict]:
    """Query Bodhi for a list of stable and pending releases.

    :param state: return only releases in this state, example: "pending"
    :return: a list of dictionaries describing releases in Bodhi
    """

    def _get_bodhi_url(page: Optional[int] = None, state: Optional[str] = None) -> str:
        """Construct Bodhi URL.

        :param state: state, e.g.: 'pending', or 'current'
        :param page: page number
        :return: Bodhi URL
        """
        query_string = ""

        if state:
            query_string += "&" if query_string else "?"
            query_string += f"state={state}"

        if page and page > 1:
            query_string += "&" if query_string else "?"
            query_string += f"page={page}"
        return BODHI_RELEASES_URL + query_string

    response_json, _ = http_get(_get_bodhi_url(state=state), as_json=True)

    releases = response_json.get("releases", [])

    # handle pagination
    pages_total = int(response_json.get("pages", "1"))
    pages_done = 1

    while pages_done < pages_total:
        response_json, _ = http_get(
            _get_bodhi_url(page=pages_done + 1, state=state), as_json=True
        )
        pages_done += 1
        releases.extend(response_json.get("releases", []))

    return releases


def get_status_file_path(work_dir: Path, task_id: str, arch: str) -> Path:
    return get_cache_dir(work_dir) / task_id / arch / "status"


def get_cache_dir(work_dir: Path) -> Path:
    """Get directory where downloaded packages are cached.

    :param work_dir: workdir
    :return: cache directory
    """
    return work_dir / "packages"


def get_cached_rpms(
    work_dir: Path,
    arches: list[str],
    task_ids: list[str],
) -> list[Path]:
    """Find workdir-cached RPM packages that match given criteria.

    :param work_dir: workdir
    :param arches: a list of arches
    :param task_ids: a list of task ids
    :return: a list of cached packages
    """
    cache_dir = get_cache_dir(work_dir)
    rpms = []

    fix_arches(arches)

    if not task_ids:
        task_dirs = list(cache_dir.glob("**/*.rpm"))
    else:
        task_dirs = [cache_dir / x for x in task_ids]

    for task_dir in task_dirs:
        if not arches:
            rpms = list(task_dir.glob("**/*.rpm"))
        else:
            for arch in arches:
                arch_dir = task_dir / arch
                rpms.extend(list(arch_dir.glob("*.rpm")))
    return rpms


def download_rpms(
    task_id: str, work_dir: Path, arches: list[str], skip_if_exists=True
) -> list[Path]:
    """Cache RPM packages.

    :param task_id: task id
    :param work_dir: workdir
    :param arches: a list of arches
    :param skip_if_exists: bool, skip downloading if there are already cached RPMs for given (task id, arch)
    :return: Path, a list of cached packages
    """
    all_rpms: list[Path] = []

    fix_arches(arches)

    for arch in arches:
        arch_dir = get_cache_dir(work_dir) / task_id / arch
        if not arch_dir.exists():
            arch_dir.mkdir(parents=True, exist_ok=True)

        if skip_if_exists:
            rpms = get_cached_rpms(work_dir, arches=[arch], task_ids=[task_id])
            if rpms:
                all_rpms.extend(rpms)
                continue

        cmd = [
            "koji",
            "download-build",
            "--arch",
            arch,
            "--noprogress",
            "--debuginfo",
            "--task-id",
            task_id,
        ]
        run_command(cmd, cwd=arch_dir)

        # It is possible that there are no RPMs for the (task id, arch) pair, and that is fine.
        # In any case, we capture the fact that the download step succeed in the "status" file.
        # This way we will be able to verify before running tests that we actually have
        # all RPMs downloaded in the cache. If they don't exist, we skip the test.
        status_file_path = get_status_file_path(work_dir, task_id, arch)
        status_file_path.write_text("done")

        rpms = get_cached_rpms(work_dir, arches=[arch], task_ids=[task_id])
        all_rpms.extend(rpms)

    return all_rpms


def is_prepared(work_dir: Path, task_ids: list[str], arches: list[str]) -> bool:
    """Check if the environment is prepared for testing.

    Right now we only check that all RPMs
    that we want to test are downloaded and cached locally.
    """
    fix_arches(arches)

    for task_id in task_ids:
        for arch in arches:
            status_file_path = get_status_file_path(work_dir, task_id, arch)

            if not status_file_path.exists():
                return False

            with open(status_file_path) as f:
                # there should be "done" on the first line in the file
                if f.readlines()[0].strip() != "done":
                    return False

        return True

    return True
