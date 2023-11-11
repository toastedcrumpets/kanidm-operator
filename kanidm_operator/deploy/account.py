from logging import Logger

import kopf
from kanidm import KanidmClient

from kanidm_operator.typing.account import AccountResource


@kopf.on.create("kanidm.github.io", "v1alpha1", "accounts")
async def on_create_account(
    spec: AccountResource, name: str, namespace: str, logger: Logger, **kwargs,
):
    client = KanidmClient()
    await client.person_account_create(
        name=spec["name"],
        display_name=spec["displayName"],
    )
    # Client not ready yet for emails/group add/legal name yet


@kopf.on.update("kanidm.github.io", "v1alpha1", "accounts")
async def on_update_account(
    spec: AccountResource, name: str, namespace: str, logger: Logger, **kwargs,
):
    client = KanidmClient()
    await client.person_account_update(
        name=spec["name"],
        display_name=spec["displayName"],
    )
    # Client not ready yet for emails/group add/legal name yet


@kopf.on.delete("kanidm.github.io", "v1alpha1", "accounts")
async def on_delete_account(
    spec: AccountResource, name: str, namespace: str, logger: Logger, **kwargs,
):
    client = KanidmClient()
    await client.person_account_delete(
        name=spec["name"],
    )