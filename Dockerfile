FROM registry.fedoraproject.org/fedora:32
LABEL maintainer "Fedora-CI"
LABEL description="rpmdeplint for fedora-ci"

ENV RPMDEPLINT_DIR=/rpmdeplint_runner/
ENV RPMDEPLINT_WORKDIR=/workdir/
ENV HOME=${RPMDEPLINT_WORKDIR}

RUN mkdir -p ${RPMDEPLINT_DIR} ${RPMDEPLINT_WORKDIR} &&\
    chmod 777 ${RPMDEPLINT_DIR} ${RPMDEPLINT_WORKDIR}

RUN dnf -y install \
    koji \
    python3-requests \
    python3-pyyaml \
    python3-pip \
    rpmdeplint \
    && dnf clean all

ADD . ${RPMDEPLINT_DIR}

WORKDIR ${RPMDEPLINT_DIR}

RUN pip install -r requirements.txt &&\
    pip install .

RUN ln -s rpmdeplint_runner/run.py run.py

WORKDIR ${RPMDEPLINT_WORKDIR}
