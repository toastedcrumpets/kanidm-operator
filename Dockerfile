FROM python:3.11-slim AS base
WORKDIR /app

RUN apt update && \
    apt install -y \
        build-essential \
        libssl-dev \
        libffi-dev \
        python3-dev \
        curl \
        pkg-config \
        libudev-dev && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install --user pipx && \
    /root/.local/bin/pipx install poetry && \
    /root/.local/bin/poetry config virtualenvs.create true && \
    /root/.local/bin/poetry config virtualenvs.in-project true

ENV PATH=/root/.local/bin:$PATH

COPY poetry.lock pyproject.toml README.md ./
COPY kanidm_operator ./kanidm_operator
RUN poetry install --only=main --no-interaction --no-ansi

FROM python:3.11-slim AS final

RUN apt update && \
    apt install -y \
        libudev1 \
        && \
    rm -rf /var/lib/apt/lists/*

# Install the KANIDM package
RUN apt update && \
    apt install -y curl

# Install Kanidm binary
# https://kanidm.github.io/kanidm_ppa/
RUN curl -s "https://kanidm.github.io/kanidm_ppa/kanidm_ppa.asc" \
    | tee /etc/apt/trusted.gpg.d/kanidm_ppa.asc >/dev/null
RUN curl -s --compressed "https://kanidm.github.io/kanidm_ppa/kanidm_ppa.list" \
    | grep $( ( . /etc/os-release && echo $VERSION_CODENAME) ) | grep stable \
    | tee /etc/apt/sources.list.d/kanidm_ppa.list
RUN apt update && \
    apt install -y kanidm

WORKDIR /app
COPY --from=base /app .
ENV KANIDM_EXEC="kanidm"
ENV PATH=/app/.venv/bin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Add -vvv after poetry to debug poetry
ENTRYPOINT ["python3","-m", "kopf", "run"]
# Add --verbose or even --debug to see more output from kopf 
CMD [ "--liveness=http://0.0.0.0:8080/healthz", "--standalone", "--all-namespaces", "-m", "kanidm_operator"]

