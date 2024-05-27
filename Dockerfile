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

RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
RUN cargo install kanidm_tools@=1.2.0

RUN pipx install poetry
RUN poetry config virtualenvs.create true

# Install python dependencies
COPY poetry.lock /app/poetry.lock
COPY pyproject.toml /app/pyproject.toml
COPY kanidm_operator /app/kanidm_operator
COPY start.py /app/
COPY README.md /app/README.md
RUN --mount=type=ssh poetry install --only=main --no-interaction --no-ansi

# Add -vvv after poetry to debug poetry
ENTRYPOINT ["poetry","run", "kopf", "run"]
# Add --verbose or even --debug to see more output from kopf 
CMD [ "--liveness=http://0.0.0.0:8080/healthz", "--standalone", "--all-namespaces", "-m", "kanidm_operator"]

