FROM python:3.11-slim as base
WORKDIR /app

# Install pipx (tooling: poetry)
RUN pip3 install --user pipx
ENV PATH=/root/.local/bin:$PATH
RUN pipx ensurepath

RUN apt update && \
    apt install -y \
        build-essential \
        openssh-client \
        libssl-dev \
        libffi-dev \
        python3-dev \
        ssh \
        curl \
        pkg-config \
        libudev-dev \
        git && \
    rm -rf /var/lib/apt/lists/*
RUN mkdir -p -m 0600 ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts

# Install the kanidm CLI tool 
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
RUN cargo install kanidm_tools@=1.2.2

# Get the python environment setup using poetry
RUN pipx install poetry
RUN poetry config virtualenvs.create true
RUN poetry config virtualenvs.in-project true

# Install python dependencies
COPY poetry.lock /app/poetry.lock
COPY pyproject.toml /app/pyproject.toml
COPY kanidm_operator /app/kanidm_operator
RUN --mount=type=ssh poetry install --only=main --no-interaction --no-ansi

FROM python:3.11-slim as final

RUN apt update && \
    apt install -y \
        libudev1 \
        && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=base /app .
COPY --from=base /root/.cargo/bin/kanidm /root/.cargo/bin/
ENV KANIDM_EXEC="/root/.cargo/bin/kanidm"
ENV PATH /app/.venv/bin:/root/.cargo/bin:/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Add -vvv after poetry to debug poetry
ENTRYPOINT ["python3","-m", "kopf", "run"]
# Add --verbose or even --debug to see more output from kopf 
CMD [ "--liveness=http://0.0.0.0:8080/healthz", "--standalone", "--all-namespaces", "-m", "kanidm_operator"]

