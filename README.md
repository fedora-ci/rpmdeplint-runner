# rpmdeplint container image

This repository contains bits needed to build a container image for [rpmdeplint](https://pagure.io/rpmdeplint). This image can be later used by Fedora CI.

## Development

For testing purposes, you can either build the image locally or you can open a pull request in this repository, and CI will build the image for you.

To build the image locally, run:

```shell
podman build -t fedoraci/rpmdeplint:devel .
```

TODO: we should validate that the final image is not completely broken; however the [runtest.sh](./runtest.sh) script is currently empty :/

### Testing

You can run and test the image locally. Simply run:

```shell
$ podman run -ti --rm fedoraci/rpmdeplint:devel /rpmdeplint_runner/run.py --help
usage: run.py [-h] {prepare,run-test} ...

Run rpmdeplint tests

optional arguments:
  -h, --help          show this help message and exit

commands:
  {prepare,run-test}
    prepare           prepare given workdir for running tests
    run-test          run the given rpmdeplint test
```

### Note about promoting to production

Merging pull requests to the master branch also triggers a build in CI. However, such images are **not*** automatically promoted and used by the CI pipelines. In order to promote a new image to production, you need to explicitly say so in the [rpmdeplint-pipeline](https://github.com/fedora-ci/rpmdeplint-pipeline/README.md#promoting-new-rpmdeplint-image-to-production) repository.
