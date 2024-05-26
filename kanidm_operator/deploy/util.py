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

class KanidmCLIClient:

    def __init__(self, kanidm_name: str, namespace: str, logger: Logger, username: str = "idm_admin"):
        self.kanidm_exec="/home/mjki2mb2/.cargo/bin/kanidm"
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
        kanidm_spec = None
        for k in kanidms["items"]:
            #logger.info(f"Checking {repr(k)}")
            if k["metadata"]["name"] == kanidm_name:
                kanidm_spec = k
                break
        if kanidm_spec is None:
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
            KANIDM_URL="https://"+kanidm_spec['spec']["domain"],
            KANIDM_NAME=username,
            KANIDM_PASSWORD=password,
        )

        self.login()

    def command(self, args):
        return subprocess.run([self.kanidm_exec, *args], env=self.env, capture_output=True)

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
