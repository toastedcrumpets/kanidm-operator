"""Shared helpers for end-to-end verification of the operator."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import yaml

KANIDM_NAMESPACE = "kanidm"
KANIDM_DOMAIN = "idm.example.com"
KANIDM_VERSION = "1.10.3"


def kubectl(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["kubectl", *args],
        capture_output=True,
        text=True,
        check=check,
    )


def kubectl_json(*args: str) -> dict:
    result = kubectl(*args, "-o", "json")
    return json.loads(result.stdout)


def secret_data(namespace: str, name: str, key: str) -> str:
    secret = kubectl_json("get", "secret", name, "-n", namespace)
    return base64.b64decode(secret["data"][key]).decode("utf-8")


def wait_processed(resource: str, name: str, timeout: str = "180s") -> None:
    kubectl(
        "wait",
        "-n",
        KANIDM_NAMESPACE,
        resource,
        name,
        "--for=jsonpath={.metadata.annotations.kanidm\\.github\\.io/processed}=true",
        f"--timeout={timeout}",
    )


class KanidmVerifier:
    """Log into Kanidm and assert server-side state via the CLI."""

    def __init__(self) -> None:
        self.kanidm_exec = os.environ.get("KANIDM_EXEC", "kanidm")
        self.env = os.environ.copy()
        password = secret_data(KANIDM_NAMESPACE, "idm-admin-credentials", "password")
        self.env.update(
            {
                "KANIDM_URL": f"https://{KANIDM_DOMAIN}",
                "KANIDM_NAME": "idm_admin",
                "KANIDM_PASSWORD": password,
            }
        )
        ca_path = os.environ.get("KANIDM_CA_PATH")
        if ca_path:
            self.env["KANIDM_CA_PATH"] = ca_path
        self._login()

    def _login(self) -> None:
        result = subprocess.run(
            [self.kanidm_exec, "login"],
            env=self.env,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise AssertionError(
                f"kanidm login failed: {result.stderr.strip() or result.stdout.strip()}"
            )

    def kanidm(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [self.kanidm_exec, *args],
            env=self.env,
            capture_output=True,
            text=True,
        )

    def assert_person(self, username: str, display_name: str, emails: list[str]) -> None:
        result = self.kanidm("person", "get", "-o", "json", username)
        assert result.returncode == 0, result.stderr or result.stdout
        assert "No matching entries" not in result.stdout, result.stdout

        data = json.loads(result.stdout)
        assert isinstance(data, dict), data
        attrs = data["attrs"]
        assert attrs["displayname"] == [display_name]
        for email in emails:
            assert email in attrs.get("mail", []), attrs.get("mail")

    def assert_group(self, name: str, members: list[str]) -> None:
        result = self.kanidm("group", "get", "-o", "json", name)
        assert result.returncode == 0, result.stderr or result.stdout

        output = result.stdout.strip()
        if "No matching group" in output:
            raise AssertionError(f"group {name!r} does not exist in Kanidm")

        data = json.loads(output)
        if isinstance(data, str):
            raise AssertionError(f"group {name!r} does not exist in Kanidm: {data}")

        group_members = data["attrs"].get("member", [])
        for member in members:
            matched = any(
                group_member == member
                or group_member.startswith(f"{member}@")
                for group_member in group_members
            )
            assert matched, group_members

    def assert_oauth2_client(self, name: str, display_name: str, origin: str) -> None:
        result = self.kanidm("system", "oauth2", "get", name)
        assert result.returncode == 0, result.stderr or result.stdout
        assert "No matching entries" not in result.stdout, result.stdout

        output = result.stdout.lstrip("-\n")
        skip_prefixes = ("oauth2_rs_scope_map:", "key_internal_data:")
        output = "\n".join(
            line for line in output.split("\n") if not line.startswith(skip_prefixes)
        )
        data = yaml.safe_load(output)
        assert data is not None, result.stdout
        rendered = yaml.safe_dump(data)
        assert display_name in rendered, rendered
        assert origin in rendered, rendered

    def assert_oauth2_k8s_secret(self, client_name: str, secret_name: str) -> None:
        result = self.kanidm("system", "oauth2", "show-basic-secret", client_name)
        assert result.returncode == 0, result.stderr or result.stdout
        kanidm_secret = result.stdout.strip()

        stored_secret = secret_data(KANIDM_NAMESPACE, secret_name, "secret")
        stored_client_id = secret_data(KANIDM_NAMESPACE, secret_name, "key")
        assert kanidm_secret == stored_secret
        assert stored_client_id == client_name


def assert_kanidm_deployment() -> None:
    deployment = kubectl_json("get", "deployment", "kanidm", "-n", KANIDM_NAMESPACE)
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    assert container["image"] == f"kanidm/server:{KANIDM_VERSION}"
    assert deployment["status"].get("readyReplicas") == 1


def assert_kanidm_configmap() -> None:
    configmap = kubectl_json("get", "configmap", "kanidm-config", "-n", KANIDM_NAMESPACE)
    server_toml = configmap["data"]["server.toml"]
    assert 'version = "2"' in server_toml
    assert "[http_client_address_info]" in server_toml
    assert f'domain = "{KANIDM_DOMAIN}"' in server_toml
    assert 'db_path = "/db/kanidm.db"' in server_toml


def assert_kanidm_ingress() -> None:
    ingress = kubectl_json("get", "ingress", "kanidm-ingress", "-n", KANIDM_NAMESPACE)
    rules = ingress["spec"]["rules"]
    assert any(rule["host"] == KANIDM_DOMAIN for rule in rules)
    assert ingress["spec"].get("ingressClassName") == "nginx"


def assert_admin_secrets() -> None:
    for secret_name in ("admin-credentials", "idm-admin-credentials"):
        secret = kubectl_json("get", "secret", secret_name, "-n", KANIDM_NAMESPACE)
        assert "password" in secret["data"]
        assert len(secret_data(KANIDM_NAMESPACE, secret_name, "password")) >= 8


def assert_https_reachable(ca_bundle: str) -> None:
    result = subprocess.run(
        ["curl", "-sI", "--cacert", ca_bundle, f"https://{KANIDM_DOMAIN}"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr.strip() or result.stdout.strip()
    status_line = result.stdout.splitlines()[0] if result.stdout else ""
    assert status_line.startswith("HTTP/"), status_line
