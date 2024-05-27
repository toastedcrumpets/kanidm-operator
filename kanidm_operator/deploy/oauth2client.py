from logging import Logger

import kopf
from kanidm_operator.typing.oauth2client import OAuth2ClientResource
from kanidm_operator.deployer import Deployer

from .util import KanidmCLIClient

@kopf.on.create("kanidm.github.io", "v1alpha1", "oauth2-clients")
@kopf.on.update("kanidm.github.io", "v1alpha1", "oauth2-clients")
async def on_create_oauth2client(
    spec: OAuth2ClientResource,
    patch: dict,
    namespace: str,
    logger: Logger,
    body: dict,
    **kwargs,
):
    cli_client = KanidmCLIClient(spec["kanidmName"], namespace, logger)
    secret = cli_client.create_oauth2client(spec['name'], spec['displayName'], spec['origin'])

    deployer = Deployer(namespace, "N/A", logger)
    deployer.deploy(
        "oauth2secret.yaml",
        name=spec["name"],
        secret=secret,
    )

#@kopf.on.field("kanidm.github.io", "v1alpha1", "oauth2-clients", field="spec.name")
#@kopf.on.field("kanidm.github.io", "v1alpha1", "oauth2-clients", field="spec.kanidmName")
#async def on_update_oauth2client_name(**kwargs):
#    raise kopf.PermanentError("User name and kanidmName cannot be changed")

@kopf.on.delete("kanidm.github.io", "v1alpha1", "oauth2-clients")
async def on_delete_oauth2client(
    spec: OAuth2ClientResource,
    name: str,
    namespace: str,
    logger: Logger,
    annotations: dict[str, str],
    **kwargs,
):
    cli_client = KanidmCLIClient(spec["kanidmName"], namespace, logger, silence_missing_kanidm=True)
    if cli_client.kanidm_spec is not None:
        cli_client.delete_oauth2client(spec['name'])
