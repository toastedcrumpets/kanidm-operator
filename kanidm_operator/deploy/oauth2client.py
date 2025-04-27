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
    # Create the oauth2 client and fetch the secret for the client
    secret = cli_client.create_oauth2client(spec['name'], spec['displayName'], spec['origin'])

    # Save the secret in a k8s secret
    deployer = Deployer(namespace, "N/A", logger)
    deployer.deploy(
        "oauth2secret.yaml",
        name=spec["name"],
        secret=secret,
        client_id=spec["name"],
        extra_annotations=spec["secret"].get("annotations", {}),
        extra_labels=spec["secret"].get("labels", {}),
    )

    # prefer-short-username is needed for gitea/forgejo
    if "prefer-short-username" in spec and spec["prefer-short-username"]:
        result = cli_client.command(['system', 'oauth2', 'prefer-short-username', spec['name']])
        if result.returncode != 0:
            raise kopf.TemporaryError(f"Failed to set prefer-short-username for oauth2 client {spec['name']}")

    # Default to enabling PKCE
    if "enable-pkce" in spec and not spec["enable-pkce"]:
        result = cli_client.command(['system', 'oauth2', 'warning-insecure-client-disable-pkce', spec['name']])
    else:
        result = cli_client.command(['system', 'oauth2', 'enable-pkce', spec['name']])
    if result.returncode != 0:
        raise kopf.TemporaryError(f"Failed to set enable-pkce for oauth2 client {spec['name']}")

    if "callback-url" in spec:
        result = cli_client.command(['system', 'oauth2', 'set-landing-url', spec['name'], spec['callback-url']])
        if result.returncode != 0:
            raise kopf.TemporaryError(f"Failed to set-landing-url for oauth2 client {spec['name']}")

    if "scope-map" in spec:
        if "group" not in spec['scope-map']:
            raise kopf.PermanentError("scope-map must contain a group entry")

        group = cli_client.get_group(spec['scope-map']['group'])
        if group is None:
            raise kopf.TemporaryError(f"Group {spec['scope-map']['group']} does not exist", delay=10)

        if "scopes" not in spec['scope-map'] or not isinstance(spec['scope-map']['scopes'], list):
            raise kopf.PermanentError("scope-map must contain a scopes entry which is an array")

        result = cli_client.command(['system', 'oauth2', 'update-scope-map', spec['name'], spec['scope-map']['group']] + spec['scope-map']['scopes'])
        if result.returncode != 0:
            raise kopf.TemporaryError(f"Failed to set scope-map for oauth2 client {spec['name']}")

    patch.setdefault("metadata", {}).setdefault("annotations", {})["kanidm.github.io/processed"] = "true"

#@kopf.on.field("kanidm.github.io"  , "v1alpha1", "oauth2-clients", field="spec.name")
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
