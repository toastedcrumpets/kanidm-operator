import json
from logging import Logger

import kopf
import os
from kanidm_operator.typing.user import UserResource
from kanidm_operator.deployer import Deployer
from kubernetes import client as kube_client, config
from kanidm_operator.deployer import slugify


@kopf.on.create("kanidm.github.io", "v1alpha1", "users")
async def on_create_user(
    spec: UserResource,
    patch: dict,
    namespace: str,
    logger: Logger,
    body: dict,
    **kwargs,
):
    logger.info(f"Trying to add user {spec['name']} to kanidm in the namespace {namespace}")
    #logger.info(f"namespace {namespace}")
    #logger.info(f"spec {repr(spec)}")
    #logger.info(f"kwargs {repr(body)}")
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        config.load_incluster_config()
    else:
        config.load_kube_config()

    core = kube_client.CustomObjectsApi()
    username="idm_admin"
    kanidms = core.list_cluster_custom_object(
            "kanidm.github.io",
            version='v1alpha1',
            plural="kanidms"
            )
    kanidm_spec = None
    for k in kanidms["items"]:
        #logger.info(f"Checking {repr(k)}")
        if k["metadata"]["name"] == spec["kanidmName"]:
            kanidm_spec = k
            break
    if kanidm_spec is None:
        raise kopf.TemporaryError(f"No Kanidm configuration named {spec['kanidmName']} found in the namespace {namespace}", delay=10)

    #logger.info(f"Getting the version {kanidm_spec['spec']}")
    deployer = Deployer(namespace, kanidm_spec['spec']['version'], logger)
    deployer.deploy(
        "userjob.yaml",
        name=f"adduser-{slugify(spec['name'])}",
        image=f"docker.io/kanidm/tools:{kanidm_spec['spec']['version']}",
        domain=kanidm_spec['spec']["domain"],
        newuser=spec["name"],
        displayName=spec["displayName"],
        email=spec["email"],
        username=username,
        password_secret=slugify(username),
    )
    logger.info(f"Started the job to add user {spec['name']} to kanidm in the namespace {namespace}")



#@kopf.on.update("kanidm.github.io", "v1alpha1", "accounts")
#async def on_update_account(
#    spec: UserResource,
#    name: str,
#    namespace: str,
#    logger: Logger,
#    **kwargs,
#):
#    pass
#    #async with InClusterKanidmClient(namespace, "admin", logger=logger) as client:
#    #    await client.person_account_update(
#    #        name=spec["name"],
#    #        display_name=spec["displayName"],
#    #        legalname=spec["legalName"],
#    #        mail=spec["emails"],
#    #    )


#@kopf.on.delete("kanidm.github.io", "v1alpha1", "accounts")
#async def on_delete_account(
#    spec: UserResource,
#    name: str,
#    namespace: str,
#    logger: Logger,
#    annotations: dict[str, str],
#    **kwargs,
#):
#    pass
#    #async with InClusterKanidmClient(namespace, "admin", logger=logger) as client:
#    #    await client.person_account_delete(annotations["kanidm.github.io/account-id"])
