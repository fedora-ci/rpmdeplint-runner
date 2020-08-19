import koji
import logging
import os
import pathlib
import re

from rpmdeplint_runner.utils import http_get, run_command, fix_arches

BUILDROOT_REPO_URL_TEMPLATE = 'https://kojipkgs.fedoraproject.org/repos/f{version}-build/{repo_id}/{arch}/'

REPO_URL_TEMPLATE = 'https://kojipkgs.fedoraproject.org/compose/{state}/latest-Fedora-{version}/compose/Everything/{arch}/os/'
DEBUGINFO_REPO_URL_TEMPLATE = 'https://kojipkgs.fedoraproject.org/compose/{state}/latest-Fedora-{version}/compose/Everything/{arch}/debug/tree/'

RAWHIDE_REPO_URL = 'https://kojipkgs.fedoraproject.org/compose/rawhide/latest-Fedora-Rawhide/compose/Everything/{arch}/os/'
RAWHIDE_DEBUGINFO_REPO_URL = 'https://kojipkgs.fedoraproject.org/compose/rawhide/latest-Fedora-Rawhide/compose/Everything/{arch}/debug/tree/'

BODHI_RELEASES_URL = 'https://bodhi.fedoraproject.org/releases/'

KOJI_HUB_URL = 'https://koji.fedoraproject.org/kojihub'
KOJI_TOP_URL = 'https://kojipkgs.fedoraproject.org'


def get_repo_urls(release_id, arch, exclude_buildroot=False, exclude_debuginfo=False):
    """Get repo URLs for given release id.

    :param release_id: str, release id, example: f33
    :param arch: str, architecture
    :param exclude_buildroot: bool, exclude buildroot repos or not
    :param exclude_debuginfo: bool, exclude debuginfo repos or not
    :return: dict, a dict where keys are repo names and values are repo URLs
    """

    result = {}

    if arch == 'armv7hl':
        # from some unknown reason, Koji uses "armv7hl" identifier, but composes use "armhfp"...
        # TODO: find out why
        arch = 'armhfp'

    version = get_version(release_id)
    repo_name = 'fedora-{version}-{arch}'.format(version=version, arch=arch)
    debug_repo_name = 'fedora-debuginfo-{version}-{arch}'.format(version=version, arch=arch)
    repo_url = RAWHIDE_REPO_URL.format(arch=arch)
    debug_repo_url = RAWHIDE_DEBUGINFO_REPO_URL.format(version=version, arch=arch)
    releases = get_releases_from_bodhi()

    if not is_rawhide(version, releases):
        if is_current(version, releases):
            state = version
            repo_url = REPO_URL_TEMPLATE.format(state=state, version=version, arch=arch)
            debug_repo_url = DEBUGINFO_REPO_URL_TEMPLATE.format(state=state, version=version, arch=arch)
        else:
            state = 'branched'
            repo_url = REPO_URL_TEMPLATE.format(state=state, version=version, arch=arch)
            debug_repo_url = DEBUGINFO_REPO_URL_TEMPLATE.format(state=state, version=version, arch=arch)

            # we need to check that this pre-release repo already exists
            if not repo_exists(repo_url):
                # there are 2 cases when the repo URL will not exist:
                # the version is too old and the repo is simply
                # no longer available, or it is too soon after
                # branching and thus the repo is not available yet.
                # if this is tha latter, we simply fall back to rawhide repo.
                if is_pending(version, releases):
                    # it's too early after branching — let's use Rawhide repo instead
                    repo_url = RAWHIDE_REPO_URL.format(arch=arch)
                    debug_repo_url = RAWHIDE_DEBUGINFO_REPO_URL.format(version=version, arch=arch)
                else:
                    raise ValueError('Repo for release "{release_id}" doesn\'t exist: {repo_url}'.format(release_id=release_id, repo_url=repo_url))

    result[repo_name] = repo_url

    if not exclude_debuginfo:
        result[debug_repo_name] = debug_repo_url

    if not exclude_buildroot:
        buildroot_repo_name = 'fedora-buildroot-{version}-{arch}'.format(version=version, arch=arch)
        buildroot_repo_url = BUILDROOT_REPO_URL_TEMPLATE.format(version=version, repo_id='latest', arch=arch)
        # there should be a file called "repo.json" in the repository directory; we fetch the file and extract
        # the real repository id from it. That way we don't have to rely on the ever-changing "latest" identifier
        # that could cause trouble during testing.
        repo_json_url = buildroot_repo_url[:buildroot_repo_url.rfind('{arch}/'.format(arch=arch))] + 'repo.json'
        response, _ = http_get(repo_json_url, as_json=True)
        if response and response.get('id'):
            buildroot_repo_url = BUILDROOT_REPO_URL_TEMPLATE.format(version=version, repo_id=response.get('id'), arch=arch)
        result[buildroot_repo_name] = buildroot_repo_url

    return result


def repo_exists(repo_url):
    """Check if given repository exists.

    :param repo_url: str, repository URL
    :return: bool, True if the repo exists, False otherwise
    """
    _, status = http_get(repo_url)
    if status == 404:
        return False
    return True


def is_pending(version, releases):
    """Check if given version is pending (is not released yet) or not.

    :param version: str, version
    :param releases: list, a list with information about fedora releases from Bodhi
    :return: bool, True if given version is a pending release, False otherwise
    """
    for release in releases:
        if release['version'] == version and release['id_prefix'] == 'FEDORA' and release['state'] == 'pending':
            return True
    return False


def is_current(version, releases):
    """Check if given version is "current" (released and supported) or not.

    :param version: str, version
    :param releases: list, a list with information about fedora releases from Bodhi
    :return: bool, True if given version is a current release, False otherwise
    """
    for release in releases:
        if release['version'] == version and release['id_prefix'] == 'FEDORA' and release['state'] == 'current':
            return True
    return False


def get_version(release_id):
    """Get version from release id.

    :param release_id: str, release id, example: f33
    :return: str, version ("f33" -> "33")
    """
    m = re.match(r"^f(\d+)$", release_id)
    if not m:
        raise ValueError('Invalid release id: %s', release_id)
    return m.group(1)


def is_rawhide(version, releases):
    """Checks if given version is Rawhide or not.

    :param version: str, fedora version, e.g. "33"
    :param releases: list, a list with information about fedora releases from Bodhi
    :return: bool, True if given version is Rawhide, False otherwise
    """
    # build a list of sorted pending versions; the last item in the list is Rawhide 
    pending_versions = sorted(
        {x['version'] for x in releases if x['id_prefix'] == 'FEDORA' and x['state'] == 'pending' and x['version'].isdigit()}
    )
    if not pending_versions:
        raise ValueError('Unable to obtain a list of pending Fedora versions')
    if version == pending_versions[-1]:
        return True
    return False


def get_releases_from_bodhi(state=None):
    """Query Bodhi for a list of stable and pending releases.

    :param state: str, return only releases in this state, example: "pending"
    :return: list, a list of dictionaries describing releases in Bodhi
    """

    def _get_bodhi_url(page=None, state=None):
        """Construct Bodhi URL.

        :param state: str, state, e.g.: 'pending', or 'current'
        :param page: int, page number
        :return: str, Bodhi URL
        """
        bodhi_url = BODHI_RELEASES_URL
        query_string = ''

        if state:
            if not query_string:
                query_string += '?'
            else:
                query_string += '&'
            query_string += 'state={state}'.format(state=state)

        if page and page > 1:
            if not query_string:
                query_string += '?'
            else:
                query_string += '&'
            query_string += 'page={page}'.format(page=page)
        return bodhi_url + query_string

    response_json, _ = http_get(_get_bodhi_url(state=state), as_json=True)

    releases = response_json.get('releases', [])

    # handle pagination
    pages_total = int(response_json.get('pages', '1'))
    pages_done = 1

    while pages_done < pages_total:
        response_json, _ = http_get(_get_bodhi_url(page=pages_done+1, state=state), as_json=True)
        pages_done += 1
        releases.extend(response_json.get('releases', []))

    return releases


def get_cache_dir(work_dir):
    """Get directory where downloaded packages are cached.

    :param work_dir: str, workdir
    :return: pathlib.Path, cache directory
    """
    return pathlib.Path(work_dir) / pathlib.Path('packages')


def get_cached_rpms(work_dir, arches=None, task_ids=None):
    """Find workdir-cached RPM packages that match given criteria.

    :param work_dir: str, workdir
    :param arches: list, a list of arches
    :param task_ids: list, a list of task ids
    :return: pathlib.Path, a list of cached packages
    """
    cache_dir = get_cache_dir(work_dir)
    rpms = []

    fix_arches(arches)

    if not task_ids:
        task_dirs = list(cache_dir.glob('**/*.rpm'))
    else:
        task_dirs = [cache_dir / pathlib.Path(str(x)) for x in task_ids]

    for task_dir in task_dirs:
        if not arches:
            rpms = list(task_dir.glob('**/*.rpm'))
        else:
            for arch in arches:
                arch_dir = task_dir / pathlib.Path(arch)
                rpms.extend(list(arch_dir.glob('*.rpm')))
    return rpms


def download_rpms(task_id, work_dir, arches, skip_if_exists=True):
    """Cache RPM packages.

    :param task_id: str, task id
    :param work_dir: str, workdir
    :param arches: list, a list of arches
    :param skip_if_exists: bool, skip downloading if there are already cached RPMs for given (task id, arch)
    :return: pathlib.Path, a list of cached packages
    """
    all_rpms = []

    fix_arches(arches)

    for arch in arches:
        arch_dir = get_cache_dir(work_dir) / pathlib.Path(str(task_id)) / pathlib.Path(arch)
        if not arch_dir.exists():
            arch_dir.mkdir(parents=True, exist_ok=True)

        if skip_if_exists:
            rpms = get_cached_rpms(work_dir, arches=[arch], task_ids=[task_id])
            if rpms:
                all_rpms.extend(rpms)
                continue

        cmd = [
            'koji',
            'download-build',
            '--arch', arch,
            '--noprogress',
            '--debuginfo',
            '--task-id', str(task_id)
        ]
        run_command(cmd, cwd=arch_dir)
        rpms = get_cached_rpms(work_dir, arches=[arch], task_ids=[task_id])
        all_rpms.extend(rpms)

    return all_rpms
