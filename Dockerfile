FROM registry.fedoraproject.org/fedora:32
LABEL maintainer "Fedora-CI"
LABEL description="rpmdeplint for fedora-ci"

ENV RPMDEPLINT_DIR=/rpmdeplint/

RUN mkdir -p ${RPMDEPLINT_DIR} &&\
    chmod 777 ${RPMDEPLINT_DIR}

WORKDIR ${RPMDEPLINT_DIR}

COPY run_rpmdeplint.py ${RPMDEPLINT_DIR}

RUN dnf -y install \
    koji \
    python3-requests \
    python3-pyyaml \
    rpmdeplint \
    && dnf clean all
