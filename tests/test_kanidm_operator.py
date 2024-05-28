import time
import subprocess
import os.path
import kopf.testing
import pytest

crd_yaml = os.path.relpath(os.path.join(os.path.dirname(__file__), '..', 'manifests/crds'))
obj_yaml = os.path.relpath(os.path.join(os.path.dirname(__file__), '..', 'manifests/operator'))
example = os.path.relpath(os.path.join(os.path.dirname(__file__), '..', 'manifests/example'))

# This fixture is automatically run, it installs the CRDs for the operator
@pytest.fixture(autouse=True)
def crd_exists():
    subprocess.run(f"kubectl apply -k {crd_yaml}",
                   check=True, timeout=10, capture_output=True, shell=True)

# This is a End-to-End test for the operator
def test_resource_lifecycle():
    # To prevent lengthy threads in the loop executor when the process exits.
    settings = kopf.OperatorSettings()
    settings.watching.server_timeout = 10

    # Create a k8s client
    from kubernetes import client, config, utils
    config.load_kube_config()
    k8s_client = client.ApiClient()
    namespace = utils.create_from_yaml(k8s_client, os.path.join(example, 'namespace.yaml'))
    print("Created namespace", namespace)

    # Run the operator and simulate some activity!
    with kopf.testing.KopfRunner(
        ['run', '--all-namespaces', '--standalone', "-m", "kanidm_operator"], #"--verbose",
        timeout=60, settings=settings,
    ) as runner:

        Kanidm = utils.create_from_yaml(k8s_client, os.path.join(example, 'kanidm.yaml'))
        print("Kanidm deployment", Kanidm, repr(Kanidm), type(Kanidm))
        time.sleep(1)  # give it some time to react


    # Ensure that the operator did not die on start, or during the operation.
    assert runner.exception is None
    assert runner.exit_code == 0

    print("operator output", repr(runner.stdout))
    # There are usually more than these messages, but we only check for the certain ones.
    #assert '[default/kopf-example-1] Creation is in progress:' in runner.stdout
    #assert '[default/kopf-example-1] Something was logged here.' in runner.stdout