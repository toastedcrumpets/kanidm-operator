import json
from logging import Logger

import kopf

from kanidm_operator.typing.account import UserResource


@kopf.on.create("kanidm.github.io", "v1alpha1", "users")
async def on_create_account(
    spec: UserResource,
    patch: dict,
    namespace: str,
    logger: Logger,
    **kwargs,
):
    #async with InClusterKanidmClient(namespace, "idm_admin", logger=logger) as client:
    #    await client.person_account_create(
    #        name=spec["name"],
    #        displayname=spec["displayName"],
    #    )
    #    account = await client.person_account_get(spec["name"])
    patch = {
        "metadata": {
            "annotations": {
                "kanidm.github.io/last-applied-spec": json.dumps(spec),
                "kanidm.github.io/account-id": account.uuid,
            }
        }
    }



@kopf.on.update("kanidm.github.io", "v1alpha1", "accounts")
async def on_update_account(
    spec: UserResource,
    name: str,
    namespace: str,
    logger: Logger,
    **kwargs,
):
    pass
    #async with InClusterKanidmClient(namespace, "admin", logger=logger) as client:
    #    await client.person_account_update(
    #        name=spec["name"],
    #        display_name=spec["displayName"],
    #        legalname=spec["legalName"],
    #        mail=spec["emails"],
    #    )


@kopf.on.delete("kanidm.github.io", "v1alpha1", "accounts")
async def on_delete_account(
    spec: UserResource,
    name: str,
    namespace: str,
    logger: Logger,
    annotations: dict[str, str],
    **kwargs,
):
    pass
    #async with InClusterKanidmClient(namespace, "admin", logger=logger) as client:
    #    await client.person_account_delete(annotations["kanidm.github.io/account-id"])
