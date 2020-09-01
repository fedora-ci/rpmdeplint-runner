FROM registry.fedoraproject.org/fedora:33
LABEL maintainer "Fedora-CI"
LABEL description="rpmdeplint for fedora-ci"

ENV RPMDEPLINT_VERSION=4989ca8
ENV RPMDEPLINT_DIR=/rpmdeplint_runner/
ENV RPMDEPLINT_RUNNER_DIR=/rpmdeplint_runner/
ENV RPMDEPLINT_WORKDIR=/workdir/
ENV HOME=${RPMDEPLINT_WORKDIR}

RUN mkdir -p ${RPMDEPLINT_DIR} ${RPMDEPLINT_RUNNER_DIR} ${RPMDEPLINT_WORKDIR} &&\
    chmod 777 ${RPMDEPLINT_DIR} ${RPMDEPLINT_RUNNER_DIR} ${RPMDEPLINT_WORKDIR}

RUN dnf -y install \
    koji \
    python3-requests \
    python3-pyyaml \
    python3-pip \
    python3-sphinx \
    python3-solv \
    python3-librepo \
    python3-hawkey \
    git \
    && dnf clean all

WORKDIR ${RPMDEPLINT_DIR}

# don't wait for official releases — install specific rpmdeplint version from git
# TODO: switch back to upstream once following commit is merged:
# https://pagure.io/fork/msrb/rpmdeplint/c/4989ca81ea0ff24bf9c68f91f23ba12316dec5b1?branch=skip-filename
RUN git clone https://pagure.io/forks/msrb/rpmdeplint.git && cd rpmdeplint/ &&\
    git reset --hard ${RPMDEPLINT_VERSION} &&\
    pip install .

ADD . ${RPMDEPLINT_RUNNER_DIR}

WORKDIR ${RPMDEPLINT_RUNNER_DIR}

RUN pip install -r requirements.txt &&\
    pip install .

RUN ln -s rpmdeplint_runner/run.py run.py

WORKDIR ${RPMDEPLINT_WORKDIR}
