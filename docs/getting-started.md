# Getting started

## Install the CRDs

```bash
kubectl apply -k github.com/juniorfoo/kanidm-operator/manifests/crds?ref=master
```

## Deploy the operator

```bash
kubectl apply -k github.com/juniorfoo/kanidm-operator/manifests/operator?ref=master
```

The operator runs in the `kanidm-system` namespace.

## Create a Kanidm instance

The examples under `manifests/example/` show a complete setup:

1. [Namespace](https://github.com/juniorfoo/kanidm-operator/blob/master/manifests/example/namespace.yaml)
2. [Kanidm server](https://github.com/juniorfoo/kanidm-operator/blob/master/manifests/example/kanidm.yaml)
3. [Users](https://github.com/juniorfoo/kanidm-operator/blob/master/manifests/example/users.yaml)
4. [Groups](https://github.com/juniorfoo/kanidm-operator/blob/master/manifests/example/groups.yaml)
5. [OAuth2 client (Forgejo)](https://github.com/juniorfoo/kanidm-operator/blob/master/manifests/example/oauth2-client.yaml)

Apply them in order:

```bash
kubectl apply -f manifests/example/namespace.yaml
kubectl apply -f manifests/example/kanidm.yaml
# wait until the Kanidm CR is processed and the deployment is Available
kubectl apply -f manifests/example/users.yaml
kubectl apply -f manifests/example/groups.yaml
kubectl apply -f manifests/example/oauth2-client.yaml
```

See the [Kanidm CRD reference](crds/kanidm.md) for all available fields.

## Admin credentials

The operator stores generated passwords for the break-glass accounts in secrets:

```bash
kubectl get secret -n kanidm admin-credentials -o jsonpath='{.data.password}' | base64 --decode
kubectl get secret -n kanidm idm-admin-credentials -o jsonpath='{.data.password}' | base64 --decode
```

Do not rotate these with `kanidmd recover-account` unless you also update the Kubernetes secrets — the operator uses them to manage Kanidm.

## End-user passwords

Each managed user receives a random password in Kanidm. Reset one from the server pod:

```bash
kubectl exec -n kanidm \
  $(kubectl get pod -n kanidm -l app.kubernetes.io/name=kanidm -o name) \
  -- kanidmd recover-account someusername
```

## OAuth2 client secrets

OAuth2 clients create a secret named `{client-name}-oauth2-credentials` in the same namespace as the CR, containing `key` (client ID) and `secret` (client secret).
