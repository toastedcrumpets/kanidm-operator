"""
Controls the deployment of kanidm in the cluster.
Will read the kanidms.kanidm.github.io CRD to deploy either:
  - In High Availability mode : n read replicas of kanidm, 1 write replica with UI
  - In Single Instance mode : 1 kanidm instance with UI as a deployment
"""

import re
import json
from logging import Logger
import time

from kubernetes import client
from kubernetes.client.models.v1_pod import V1Pod
from kubernetes.client.models.v1_pod_status import V1PodStatus
import kopf

from kanidm_operator.deployer import Deployer
from kanidm_operator.typing.kanidm import KanidmResource
from kubernetes.stream import stream

def parse_recover_account_password(output: str) -> str | None:
    """Extract a recovered password from kanidmd output (JSON or log format)."""
    json_match = re.search(r'\{"password"\s*:\s*"([^"]+)"\}', output)
    if json_match is not None:
        return json_match.group(1)

    log_match = re.search(r'new_password:\s*"([^"]+)"', output)
    if log_match is not None:
        return log_match.group(1)

    return None

@kopf.on.create("kanidm.github.io", "v1alpha1", "kanidms")
async def on_create_kanidms(
    spec: KanidmResource,
    name: str,
    namespace: str,
    logger: Logger,
    patch: dict,
    **kwargs,
):
    logger.info(f"Creating kanidm instance {name} in namespace {namespace}")
    deployer = Deployer(namespace, spec["version"], logger)

    deployer.deploy(
        "certificate.yaml",
        hostname=spec["domain"],
        certificate_issuer=spec["certificate"]["issuer"],
        version=spec["version"],
    )
    deployer.deploy(
        "pvc-backups.yaml",
        backup_storage_class=spec["backup"]["storageClass"],
        backup_storage_size=spec["backup"]["storageSize"],
        backup_storage_annotations=spec["backup"].get("storageAnnotations", {}),
        backup_storage_labels=spec["backup"].get("storageLabels", {}),
    )
    deployer.deploy(
        "pvc-db.yaml",
        db_storage_class=spec["database"]["storageClass"],
        db_storage_size=spec["database"]["storageSize"],
        db_storage_annotations=spec["database"].get("storageAnnotations", {}),
        db_storage_labels=spec["database"].get("storageLabels", {}),
    )
    deployer.deploy(
        "service.yaml",
        http_port=spec["webPort"],
        ldap_port=spec["ldapPort"],
    )
    deployer.deploy(
        "server.toml",
        domain=spec["domain"],
        log_level=spec.get("logLevel", "info"),
        ldap_port=spec.get("ldapPort", "3890"),
        http_port=spec.get("webPort", "8443"),
        db_fs_type=spec["database"]["fsType"],
        db_arc_size=spec["database"]["arcSize"],
        backup_enabled=spec["backup"]["enabled"],
        backup_schedule=spec["backup"]["schedule"],
        backup_versions=spec["backup"]["versions"],
        trust_x_forwarded_for=spec["ingress"]["trustXForwardedFor"],
    )

    if not spec["highAvailability"]["enabled"]:
        deployer.deploy(
            "deployment.yaml",
            http_port=spec.get("webPort", "8443"),
            ldap_port=spec.get("ldapPort", "3890"),
            image=f"kanidm/server:{spec['version']}",
        )
    # TODO: Handle HighAvailability mode

    if spec.get("ingress").get("enabled", False):
        deployer.deploy(
            "ingress.yaml",
            hostname=spec["domain"],
            http_port=spec["webPort"],
            ingress_class_name=spec["ingress"].get("ingressClassName", "nginx"),
            annotations={} if "annotations" not in spec["ingress"] else spec["ingress"]["annotations"],
        )

    logger.info(f"All k8s resources for kanidm {name} have been deployed, waiting for pod to be ready")
    done = False
    core = client.CoreV1Api()
    while not done:
        pods: list[V1Pod] = core.list_namespaced_pod(
            namespace,
            label_selector="app.kubernetes.io/name=kanidm",
        ).items
        
        if len(pods) == 0:
            logger.info(f"Waiting for kanidm {name} pod to be created")
            time.sleep(5)
            continue

        pod = pods[0]
        status: V1PodStatus = pod.status

        if status.phase != "Running":
            logger.info(f"Waiting for kanidm {name} pod to be ready, current status: {status.phase}")
            time.sleep(5)
            continue

        logger.info("Kanidm pod is running, trying to fetch admin and idm_admin passwords")
        
        resp = stream(core.connect_get_namespaced_pod_exec,
                pod.metadata.name,
                namespace,
                container="kanidm",
                command=["kanidmd", "recover-account", "admin"],
                stderr=False, stdin=False, stdout=True, tty=False,
            )
        admin_password = parse_recover_account_password(resp)
        if admin_password is None:
            logger.info(f"Failed to parse admin password, perhaps kanidm is still booting? Retrying")
            # If kanidm has not booted yet, then the socket will not be available, so wait a bit
            time.sleep(2)
            continue
        resp = stream(core.connect_get_namespaced_pod_exec,
                pod.metadata.name,
                namespace,
                container="kanidm",
                command=["kanidmd", "recover-account", "idm_admin"],
                stderr=False, stdin=False, stdout=True, tty=False,
        )
        idm_admin_password = parse_recover_account_password(resp)
        if idm_admin_password is None:
            logger.warning(f"Failed to parse idm_admin password, this should not happen!")
            # If kanidm has not booted yet, then the socket will not be available, so wait a bit
            time.sleep(2)
            continue
        deployer.deploy(
            "usersecret.yaml",
            username="admin",
            password=admin_password,
        )
        deployer.deploy(
            "usersecret.yaml",
            username="idm_admin",
            password=idm_admin_password,
        )
        logger.info("Kanidm admin and idm_admin passwords have been fetched and stored in secrets")
        done = True
    
    patch.setdefault("metadata", {}).setdefault("annotations", {})["kanidm.github.io/processed"] = "true"

@kopf.on.update("kanidm.github.io", "v1alpha1", "kanidms")
async def on_update_kanidms(
    spec: KanidmResource,
    name: str,
    namespace: str,
    logger: Logger,
    **kwargs,
):
    pass
