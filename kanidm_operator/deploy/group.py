from logging import Logger

import kopf

from kanidm_operator.typing.group import GroupResource
from .util import KanidmCLIClient


@kopf.on.create("kanidm.github.io", "v1alpha1", "groups")
async def on_create_group(
    spec: GroupResource,
    patch: dict,
    namespace: str,
    logger: Logger,
    **kwargs,
):
    logger.info(f"Trying to create group {spec['name']} to kanidm in the namespace {namespace}")
    cli_client = KanidmCLIClient(spec["kanidmName"], namespace, logger)
    cli_client.create_group(spec['name'])
    cli_client.set_group_members(spec['name'], spec['members'])

@kopf.on.field("kanidm.github.io", "v1alpha1", "groups", field="spec.name")
@kopf.on.field("kanidm.github.io", "v1alpha1", "groups", field="spec.kanidmName")
async def on_update_group_name(**kwargs):
    raise kopf.PermanentError("Group name cannot be changed")


@kopf.on.field("kanidm.github.io", "v1alpha1", "groups", field="spec.members")
async def on_update_group_members(
    spec: GroupResource,
    annotations: dict[str, str],
    namespace: str,
    logger: Logger,
    **kwargs,
):
    cli_client = KanidmCLIClient(spec["kanidmName"], namespace, logger)
    cli_client.set_group_members(spec['name'], spec['members'])

@kopf.on.delete("kanidm.github.io", "v1alpha1", "groups")
async def on_delete_group(
    spec: GroupResource,
    namespace: str,
    logger: Logger,
    **kwargs,
):
    cli_client = KanidmCLIClient(spec["kanidmName"], namespace, logger, silence_missing_kanidm=True)
    if cli_client.kanidm_spec is not None:
        cli_client.delete_group(spec['name'])
