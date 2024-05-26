from logging import Logger

import kopf
from kanidm_operator.typing.user import UserResource
from kanidm_operator.deployer import Deployer
from kanidm_operator.deployer import slugify

from .util import KanidmCLIClient
import subprocess

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
    cli_client = KanidmCLIClient(spec["kanidmName"], namespace, logger)
    cli_client.delete_user(spec['name'])
