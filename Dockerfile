FROM registry.fedoraproject.org/fedora:38
LABEL maintainer "Fedora-CI"
LABEL description="rpmdeplint for fedora-ci"

ENV RPMDEPLINT_BRANCH=fedora-ci
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

# https://pagure.io/fork/msrb/rpmdeplint/tree/rpmdeplint-1.4-fedora-ci
RUN git clone https://pagure.io/forks/msrb/rpmdeplint.git && cd rpmdeplint/ &&\
    git checkout ${RPMDEPLINT_BRANCH} &&\
    pip install .

ADD . ${RPMDEPLINT_RUNNER_DIR}

WORKDIR ${RPMDEPLINT_RUNNER_DIR}

RUN pip install -r requirements.txt &&\
    pip install .

RUN ln -s rpmdeplint_runner/run.py run.py

WORKDIR ${RPMDEPLINT_WORKDIR}
