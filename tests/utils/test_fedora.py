from rpmdeplint_runner.utils.fedora import get_repo_urls


# TODO: do not actually query Bodhi – tests will stop working in future


def test_get_repo_urls():
    """Test get_repo_urls().

    TODO: we need more tests, especially for pending releases and rawhide.
    """
    repo_urls = get_repo_urls(
        "f32", "x86_64", exclude_buildroot=False, exclude_debuginfo=False
    )
    assert len(repo_urls) == 3

    # check repo names
    assert "fedora-32-x86_64" in repo_urls
    assert "fedora-debuginfo-32-x86_64" in repo_urls
    assert "fedora-buildroot-32-x86_64" in repo_urls

    # check that the buildroot URL doesn't point to the "latest" repo;
    # the "/latest/" part of the URL should have been replaced by the real repo id
    assert "/latest/" not in repo_urls["fedora-buildroot-32-x86_64"]
