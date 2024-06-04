import os
from kubernetes import client as kube_client, config
import kopf
from kubernetes.client.models.v1_secret import V1Secret
from kubernetes.client.models.v1_secret_list import V1SecretList
from kanidm_operator.deployer import slugify
from logging import Logger
from base64 import b64decode
import subprocess
import json
import yaml

kanidm_exec = os.environ.get("KANIDM_EXEC", "kanidm")

class KanidmCLIClient:
    def __init__(self, kanidm_name: str, namespace: str, logger: Logger, username: str = "idm_admin", silence_missing_kanidm: bool = False):
        self.logger = logger

        if os.getenv("KUBERNETES_SERVICE_HOST"):
            config.load_incluster_config()
        else:
            config.load_kube_config()

        customapi = kube_client.CustomObjectsApi()
        
        # First discover the kanidm instance we're working on
        kanidms = customapi.list_cluster_custom_object(
                "kanidm.github.io",
                version='v1alpha1',
                plural="kanidms"
                )
        self.kanidm_spec = None
        for k in kanidms["items"]:
            #logger.info(f"Checking {repr(k)}")
            if k["metadata"]["name"] == kanidm_name:
                self.kanidm_spec = k
                break

        
        if self.kanidm_spec is None:
            if silence_missing_kanidm:
                return
            raise kopf.TemporaryError(f"No Kanidm configuration named {kanidm_name} found in the namespace {namespace}", delay=10)

        coreapi = kube_client.CoreV1Api()
        # Now get the user's password secret
        secrets: V1SecretList = coreapi.list_namespaced_secret(
            namespace,
            label_selector=f"kanidm.github.io/credentials-for={slugify(username)}",
        )

        if len(secrets.items) == 0:
            raise kopf.TemporaryError(f"No secret found for user {username} in the namespace {namespace}", delay=10)
        if len(secrets.items) > 1:
            raise kopf.TemporaryError(f"Multiple secrets for {username} in the namespace {namespace} found!", delay=10)
        
        #logger.info(f"Secrets are {repr(secrets.items)}")

        secret: V1Secret = secrets.items[0]
        if "password" not in secret.data:
            raise kopf.TemporaryError(f"Secret for {username} in the namespace {namespace} does not contain a password!", delay=10)
        
        password = b64decode(secret.data["password"].encode("utf-8")).decode("utf-8")

        self.env = dict(
            KANIDM_URL="https://"+self.kanidm_spec['spec']["domain"],
            KANIDM_NAME=username,
            KANIDM_PASSWORD=password,
        )

        self.login()

    def command(self, args):
        return subprocess.run([kanidm_exec, *args], env=self.env, capture_output=True)

    def login(self):        
        login_result = self.command(["login"])
        if login_result.returncode != 0:
            raise kopf.TemporaryError(f"Failed to login to kanidm, stdout={login_result.stdout}, stderr={login_result.stderr}", delay=10)

    def get_user(self, username):
        get_result = self.command(["person", "get", "-o", "json", username])
        if get_result.returncode != 0:
            raise kopf.TemporaryError(f"Failed to get user ({get_result.returncode}), stdout={get_result.stdout.decode()}, stderr={get_result.stderr.decode()}", delay=10)
        
        #We had a successful query, check if there's no matching entries
        if "No matching entries" in get_result.stdout.decode():
            return None
        
        try:
            return json.loads(get_result.stdout)
        except json.JSONDecodeError as e:
            raise kopf.TemporaryError(f"Failed to parse user data from kanidm CLI for {username} ({e})", delay=10)

    def get_group(self,name):
        get_result = self.command(["group", "get", "-o", "json", name])
        if get_result.returncode != 0:
            raise kopf.TemporaryError(f"Failed to get group ({get_result.returncode}), stdout={get_result.stdout.decode()}, stderr={get_result.stderr.decode()}", delay=10)
        
        #We had a successful query, check if there's no matching entries
        if "No matching group" in get_result.stderr.decode():
            return None
        
        try:
            return json.loads(get_result.stdout)
        except json.JSONDecodeError as e:
            raise kopf.TemporaryError(f"Failed to parse group data from kanidm CLI for {name} ({e})\nstdout={get_result.stdout.decode()}\nstderr={get_result.stderr.decode()}", delay=10)

    def get_oauth2client(self,name):
        get_result = self.command(["system", "oauth2", "get", name])
        if get_result.returncode != 0:
            raise kopf.TemporaryError(f"Failed to get oauth2client ({get_result.returncode}), stdout={get_result.stdout.decode()}, stderr={get_result.stderr.decode()}", delay=10)
        
        #We had a successful query, check if there's no matching entries
        if "No matching entries" in get_result.stdout.decode():
            return None
        
        output = get_result.stdout.decode().lstrip('-\n')
        # We know that the output contains incorrectly formatted lines for YAML
        # https://github.com/kanidm/kanidm/issues/1998
        # We can fix this by removing the line starting with "oauth2_rs_scope_map:"
        output = "\n".join([l for l in output.split("\n") if not l.startswith("oauth2_rs_scope_map:")])
        try:
            return yaml.safe_load(output)
        except yaml.YAMLError as e:
            raise kopf.TemporaryError(f"Failed to parse oauth2client data from kanidm CLI for {name} ({e})\nstdout={get_result.stdout.decode()}\nstderr={get_result.stderr.decode()}", delay=10)

    def create_user(self, username: str, displayname: str):
        # First, check if user already exists
        existing_user_data = self.get_user(username)
        if existing_user_data == None:
            create_result = self.command(["person", "create", username, displayname])
            if create_result.returncode != 0:
                raise kopf.TemporaryError(f"Failed to create user ({create_result.returncode}), stdout={create_result.stdout.decode()}, stderr={create_result.stderr.decode()}", delay=10)
            # Success, we created the user!
            return    

        self.logger.warning(f"User {username} already exists, not creating. {existing_user_data}")
        
        # Now we check if the already existing user needs a display name change
        if existing_user_data['attrs']["displayname"] != displayname:
            update_result = self.command(["person", "update", username, "--displayname", displayname])
            if update_result.returncode != 0:
                raise kopf.TemporaryError(f"Failed to update user displayname ({update_result.returncode}), stdout={update_result.stdout.decode()}, stderr={update_result.stderr.decode()}", delay=10)
            # Success, we updated the user displayname!
        return
    
    def delete_user(self, username: str):
        result = self.command(["person", "delete", username])
        if result.returncode != 0:
            raise kopf.TemporaryError(f"Failed to delete user ({result.returncode}), stdout={result.stdout.decode()}, stderr={result.stderr.decode()}", delay=10)

    def set_user_emails(self, username: str, emails: list[str]):
        result = self.command(["person", "update", username] + [k for m in emails for k in ["-m", m]])
        if result.returncode != 0:
            raise kopf.TemporaryError(f"Failed to update emails for user ({result.returncode}), stdout={result.stdout.decode()}, stderr={result.stderr.decode()}", delay=10)

    def create_group(self, name: str):
        # First, check if user already exists
        existing_group_data = self.get_group(name)
        if existing_group_data == None:
            create_result = self.command(["group", "create", name])
            if create_result.returncode != 0:
                raise kopf.TemporaryError(f"Failed to create group ({create_result.returncode}), stdout={create_result.stdout.decode()}, stderr={create_result.stderr.decode()}", delay=10)
            # Success, we created the user!
            return    

        self.logger.warning(f"Group {name} already exists, not creating. {existing_group_data}")

    def set_group_members(self, name: str, members: list[str]):
        result = self.command(["group", "set-members", name] + members)
        if result.returncode != 0:
            raise kopf.TemporaryError(f"Failed to update members for group ({result.returncode}), stdout={result.stdout.decode()}, stderr={result.stderr.decode()}", delay=10)
        
    def delete_group(self, name: str):
        result = self.command(["group", "delete", name])
        if result.returncode != 0:
            raise kopf.TemporaryError(f"Failed to delete group ({result.returncode}), stdout={result.stdout.decode()}, stderr={result.stderr.decode()}", delay=10)

    def create_oauth2client(self, name: str, displayname: str, origin: str):
        # First, check if user already exists
        existing_client_data = self.get_oauth2client(name)
        if existing_client_data == None:
            create_result = self.command(["system", "oauth2", "create", name, displayname, origin])
            if create_result.returncode != 0:
                raise kopf.TemporaryError(f"Failed to create oauth2 client ({create_result.returncode}), stdout={create_result.stdout.decode()}, stderr={create_result.stderr.decode()}", delay=10)
            # Success, we created the oauth token
        else:
            self.logger.warning(f"OAuth2 client {name} already exists, not creating. {existing_client_data}")

        secret  = self.command(["system", "oauth2", "show-basic-secret", name])
        if secret.returncode != 0:
            raise kopf.TemporaryError(f"Failed to get secret for oauth2 client ({secret.returncode}), stdout={secret.stdout.decode()}, stderr={secret.stderr.decode()}", delay=10)
        
        return secret.stdout.decode().strip()
    
    def delete_oauth2client(self, name: str):
        result = self.command(["system", "oauth2", "delete", name])
        if result.returncode != 0:
            raise kopf.TemporaryError(f"Failed to delete oauth2client ({result.returncode}), stdout={result.stdout.decode()}, stderr={result.stderr.decode()}", delay=10)
