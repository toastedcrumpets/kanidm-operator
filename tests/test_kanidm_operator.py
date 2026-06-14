import os
import os.path
import socket
import subprocess

import kopf.testing
import pytest

from tests.helpers import (
    KanidmVerifier,
    assert_admin_secrets,
    assert_https_reachable,
    assert_kanidm_configmap,
    assert_kanidm_deployment,
    assert_kanidm_ingress,
    wait_processed,
)

crd_yaml = os.path.relpath(os.path.join(os.path.dirname(__file__), "..", "manifests/crds"))
example = os.path.relpath(os.path.join(os.path.dirname(__file__), "..", "manifests/example"))
fixtures = os.path.join(os.path.dirname(__file__), "fixtures")
project_root = os.path.relpath(os.path.join(os.path.dirname(__file__), ".."))
default_ca_bundle = os.path.join(project_root, "KanidmCA.crt")


def _clear_kanidm_namespace() -> None:
    """Remove the test namespace, including kopf finalizers if deletion stalls."""
    subprocess.run(
        "kubectl delete namespace kanidm --ignore-not-found --wait=false",
        shell=True,
        check=False,
        capture_output=True,
    )
    wait = subprocess.run(
        "kubectl wait --for=delete namespace/kanidm --timeout=180s",
        shell=True,
        check=False,
        timeout=200,
        capture_output=True,
    )
    if wait.returncode != 0:
        for resource in ("group", "user", "oauth2-clients", "kanidm"):
            subprocess.run(
                f"kubectl get {resource} -n kanidm -o name 2>/dev/null | "
                "xargs -r -I{} kubectl patch {} -n kanidm "
                "--type=merge -p '{\"metadata\":{\"finalizers\":[]}}'",
                shell=True,
                check=False,
                capture_output=True,
            )
        subprocess.run(
            "kubectl patch namespace kanidm --type=merge "
            "-p '{\"spec\":{\"finalizers\":[]}}'",
            shell=True,
            check=False,
            capture_output=True,
        )
        subprocess.run(
            "kubectl wait --for=delete namespace/kanidm --timeout=60s",
            shell=True,
            check=False,
            timeout=70,
            capture_output=True,
        )


@pytest.fixture(autouse=True)
def crd_exists():
    _clear_kanidm_namespace()
    subprocess.run(
        f"kubectl apply -k {crd_yaml}",
        check=True,
        timeout=10,
        capture_output=True,
        shell=True,
    )


def _ca_bundle() -> str:
    bundle = os.environ.get("REQUESTS_CA_BUNDLE")
    if bundle:
        return bundle
    if os.path.exists(default_ca_bundle):
        return default_ca_bundle
    return "/etc/ssl/certs/ca-certificates.crt"


def test_resource_lifecycle():
    settings = kopf.OperatorSettings()
    settings.watching.server_timeout = 10
    ca_bundle = _ca_bundle()

    subprocess.run(
        f"kubectl apply -f {os.path.join(example, 'namespace.yaml')}",
        shell=True,
        check=True,
        timeout=30,
        capture_output=True,
    )

    with kopf.testing.KopfRunner(
        ["run", "--all-namespaces", "--standalone", "-m", "kanidm_operator"],
        timeout=600,
        settings=settings,
    ) as runner:
        subprocess.run(
            f"kubectl apply -f {os.path.join(example, 'kanidm.yaml')}",
            shell=True,
            check=True,
            timeout=30,
            capture_output=True,
        )
        wait_processed("kanidm", "kanidm-instance")

        subprocess.run(
            "kubectl wait --for=condition=Available deployment kanidm -n kanidm --timeout=90s",
            shell=True,
            check=True,
        )
        subprocess.run(
            "kubectl wait -n kanidm certificate kanidm-ingress-cert --for=condition=Ready --timeout=90s",
            shell=True,
            check=True,
            timeout=120,
            capture_output=True,
        )

        assert_kanidm_deployment()
        assert_kanidm_configmap()
        assert_kanidm_ingress()
        assert_admin_secrets()

        socket.gethostbyname("idm.example.com")
        assert_https_reachable(ca_bundle)

        subprocess.run(
            f"kubectl apply -f {os.path.join(example, 'users.yaml')}",
            shell=True,
            check=True,
            timeout=30,
            capture_output=True,
        )
        wait_processed("user", "marcus")
        KanidmVerifier().assert_person("marcus", "Marcus", ["marcus@example.com"])

        subprocess.run(
            f"kubectl apply -f {os.path.join(example, 'groups.yaml')}",
            shell=True,
            check=True,
            timeout=30,
            capture_output=True,
        )
        wait_processed("group", "git-users")
        KanidmVerifier().assert_group("git-users", ["marcus"])

        subprocess.run(
            f"kubectl apply -f {os.path.join(fixtures, 'oauth2-forgejo.yaml')}",
            shell=True,
            check=True,
            timeout=30,
            capture_output=True,
        )
        wait_processed("oauth2-clients", "forgejo-oauth")
        verifier = KanidmVerifier()
        verifier.assert_oauth2_client("forgejo", "Forgejo", "https://git.example.com")
        verifier.assert_oauth2_k8s_secret("forgejo", "forgejo-oauth2-credentials")

    assert runner.exception is None
    assert runner.exit_code == 0
