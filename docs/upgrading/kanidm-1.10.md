# Upgrading to Kanidm 1.10

This guide covers operator changes for Kanidm **1.10.3**, breaking API differences discovered during the upgrade, and how to run the test suite locally.

## Summary

| Area | Change |
|------|--------|
| Server image | Set `spec.version: 1.10.3` (or your target 1.10.x patch) on the `Kanidm` CR |
| `server.toml` | Must use config **version 2** (required since Kanidm 1.6) |
| Reverse proxy trust | `trust_x_forward_for` replaced by `[http_client_address_info]` |
| `kanidmd recover-account` | `-o json` removed; passwords appear in log output |
| `kanidm group get -o json` | Missing groups return a JSON **string**, not an object |
| CLI client | Must match server version (1.10.x) |

## Existing deployments

Kanidm requires **sequential minor-version upgrades**. You cannot jump from 1.5 directly to 1.10.

Example path: 1.5 → 1.6 → … → 1.10.

See the [Kanidm server update guide](https://kanidm.github.io/kanidm/stable/server_updates.html) before upgrading production data.

Fresh installs can set `spec.version: 1.10.3` directly.

## Operator code changes

### Server configuration

Kanidm 1.6+ requires `version = "2"` in `server.toml`. The deprecated `trust_x_forward_for` boolean is replaced with:

```toml
[http_client_address_info]
x-forward-for = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8"]
```

when `spec.ingress.trustXForwardedFor: true`. The `role = "WriteReplica"` setting was removed.

### Admin password recovery

Kanidm 1.10 removed `-o json` from `kanidmd recover-account`. Passwords now appear as log lines:

```
new_password: "…"
```

The operator parses both the legacy JSON blob and the new log format.

### CLI compatibility

**Group lookup:** `kanidm group get -o json <name>` may return a JSON-encoded string for missing groups. The operator treats that as “not found”.

**Environment:** CLI subprocesses inherit the full process environment so `KANIDM_CA_PATH` and local wrappers work correctly.

### Resource limits

Kanidm 1.10 needs more memory than 1.5. The deployment template uses **512Mi** limit / **256Mi** request.

## Running tests locally

The e2e test mirrors CI: KIND cluster, ingress-nginx, cert-manager, and a self-signed CA.

### Prerequisites

- Docker, `kubectl`, Python 3.11+, [kind](https://kind.sigs.k8s.io/), `curl`, `openssl`

### Install the Kanidm CLI (matches CI)

```bash
curl -s "https://kanidm.github.io/kanidm_ppa/kanidm_ppa.asc" \
  | sudo tee /etc/apt/trusted.gpg.d/kanidm_ppa.asc >/dev/null
curl -s --compressed "https://kanidm.github.io/kanidm_ppa/kanidm_ppa.list" \
  | grep $( ( . /etc/os-release && echo $VERSION_CODENAME) ) | grep stable \
  | sudo tee /etc/apt/sources.list.d/kanidm_ppa.list
sudo apt update && sudo apt install -y kanidm
export KANIDM_EXEC=kanidm
```

### Cluster setup

Use a dedicated kubeconfig so KIND does not switch your default kubectl context:

```bash
kind create cluster --name kanidm-operator --config tests/kind-config.yaml \
  --kubeconfig "${PWD}/.kube/kind-kanidm-operator"
export KUBECONFIG="${PWD}/.kube/kind-kanidm-operator"
```

Or omit `--kubeconfig` and run `kubectl config use-context default` when you are done testing.

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/component=controller -n ingress-nginx --timeout=120s
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.5/cert-manager.yaml
kubectl wait --for=condition=Available deployment cert-manager-webhook -n cert-manager --timeout=120s

openssl genrsa -out KanidmCA.key 4096
openssl req -x509 -new -nodes -key KanidmCA.key -sha256 -days 1826 -out KanidmCA.crt \
  -subj '/CN=KanidmRoot CA/C=AT/ST=Vienna/L=Vienna/O=Kanidm' \
  -addext 'basicConstraints=critical,CA:TRUE' \
  -addext 'keyUsage=critical,keyCertSign,cRLSign'
kubectl create secret -n cert-manager tls kanidm-ca --cert=KanidmCA.crt --key=KanidmCA.key
kubectl apply -f tests/cluster-issuer.yaml

INGRESS_IP=$(docker container inspect kanidm-operator-control-plane --format '{{ .NetworkSettings.Networks.kind.IPAddress }}')
echo "$INGRESS_IP idm.example.com" | sudo tee -a /etc/hosts
sudo cp KanidmCA.crt /usr/local/share/ca-certificates/KanidmCA.crt
sudo update-ca-certificates --fresh
```

### Run tests

```bash
poetry install
poetry run pytest -v
```

## Test coverage

| Layer | What it verifies |
|-------|------------------|
| `test_server_config.py` | Config version 2, proxy settings, password parsing |
| `test_kanidm_operator.py` | Full lifecycle: K8s resources, HTTPS, Kanidm user/group/OAuth2 state, secret contents |

The e2e test does not yet cover update/delete flows or the Grafana OAuth2 example manifest.

## CI

GitHub Actions generates the test CA with `keyUsage` extensions and runs `pytest` plus `mkdocs build --strict` on every pull request.
