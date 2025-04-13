FROM harbor.app.clemson.edu/dockerhub-proxy/python:3.12-slim-bullseye AS builder

WORKDIR /usr/src/app

COPY . .

RUN python -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    export https_proxy=http://proxy.app.clemson.edu:8080 && pip install --no-cache-dir . && \
    deactivate

FROM harbor.app.clemson.edu/dockerhub-proxy/python:3.12-slim-bullseye

RUN addgroup --system netdev && useradd -m --shell /bin/bash -G netdev appuser && echo "appuser ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

COPY --from=builder /opt/venv /opt/venv

# Activate virtual environment for all users
ENV PATH="/opt/venv/bin:$PATH"

USER appuser

CMD [ "cu-vcenter-discovery" ]