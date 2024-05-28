from logging import Logger

import kopf
from kanidm_operator.typing.user import UserResource

from .util import KanidmCLIClient

@kopf.on.create("kanidm.github.io", "v1alpha1", "users")
@kopf.on.update("kanidm.github.io", "v1alpha1", "users")
async def on_create_user(
    spec: UserResource,
    patch: dict,
    namespace: str,
    logger: Logger,
    body: dict,
    **kwargs,
):
    logger.info(f"Trying to add user {spec['name']} to kanidm in the namespace {namespace}")
    cli_client = KanidmCLIClient(spec["kanidmName"], namespace, logger)
    cli_client.create_user(spec['name'], spec['displayName'])
    cli_client.set_user_emails(spec['name'], spec['emails'])

    patch.setdefault("metadata", {}).setdefault("annotations", {})["kanidm.github.io/processed"] = "true"

#@kopf.on.field("kanidm.github.io", "v1alpha1", "users", field="spec.name")
#@kopf.on.field("kanidm.github.io", "v1alpha1", "users", field="spec.kanidmName")
#async def on_update_group_name(**kwargs):
#    raise kopf.PermanentError("User name and kanidmName cannot be changed")

@kopf.on.delete("kanidm.github.io", "v1alpha1", "users")
async def on_delete_user(
    spec: UserResource,
    name: str,
    namespace: str,
    logger: Logger,
    annotations: dict[str, str],
    **kwargs,
):
    logger.info(f"Trying to add user {spec['name']} to kanidm in the namespace {namespace}")
    # If kanidm is already gone, then don't worry about deleting
    cli_client = KanidmCLIClient(spec["kanidmName"], namespace, logger, silence_missing_kanidm=True)
    if cli_client.kanidm_spec is not None:
        cli_client.delete_user(spec['name'])
