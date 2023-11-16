FROM registry.fedoraproject.org/fedora:39
LABEL maintainer "Fedora-CI"
LABEL description="rpmdeplint for fedora-ci"

ENV RPMDEPLINT_RUNNER_DIR=/rpmdeplint_runner/
ENV RPMDEPLINT_WORKDIR=/workdir/
ENV HOME=${RPMDEPLINT_WORKDIR}

RUN mkdir -p ${RPMDEPLINT_RUNNER_DIR} ${RPMDEPLINT_WORKDIR} &&\
    chmod 777 ${RPMDEPLINT_RUNNER_DIR} ${RPMDEPLINT_WORKDIR}

RUN dnf -y install 'dnf-command(copr)' && \
    dnf -y copr enable @osci/rpmdeplint && \
    dnf -y install \
    koji \
    python3-pip \
    git \
    rpmdeplint \
    && dnf clean all

ADD . ${RPMDEPLINT_RUNNER_DIR}
RUN cd ${RPMDEPLINT_RUNNER_DIR} && \
    pip install -r requirements.txt && \
    pip install . && \
    ln -s rpmdeplint_runner/run.py run.py

WORKDIR ${RPMDEPLINT_WORKDIR}
