# Kanidm operator

A Kubernetes operator that deploys and manages one or more [Kanidm](https://kanidm.com/) instances.

Why use this operator? This operator lets you define the users, groups, and even
oauth endpoints in your kubernetes configuration. This means you can run your
entire Single Sign On/authentication as an ``almost'' stateless deployment. It
cannot be totally stateless, as a database is needed to store current
passwords/let users change them; however, all the configuration can be!

## Documentation

Full documentation is built with [MkDocs](https://www.mkdocs.org/) from the [`docs/`](docs/) directory:

- **Online:** run `poetry install --with docs && poetry run mkdocs serve` and open http://127.0.0.1:8000
- **Topics:** [getting started](docs/getting-started.md), [CRD reference](docs/crds/kanidm.md), [developing](docs/developing.md), [Kanidm 1.10 upgrade](docs/upgrading/kanidm-1.10.md)

## Requirements

* [cert-manager](https://cert-manager.io/): Kanidm needs to generate TLS
certificates for its operation and uses a certificate manager to generate these.
* An ingress controller with SSL/HTTPS: A HTTPS-secured ingress to the kanidm instance is needed as the operator uses the [Kanidm Client Tools](https://kanidm.github.io/kanidm/stable/client_tools.html) to carry out configuration.

## Getting Started

First, apply the custom resource definitions:

```bash
kubectl apply -k github.com/juniorfoo/kanidm-operator/manifests/crds?ref=master
```

Then, deploy the operator:

```bash
kubectl apply -k github.com/juniorfoo/kanidm-operator/manifests/operator?ref=master
```

This will deploy the operator in the `kanidm-system` namespace. You are now ready to configure/deploy as many Kanidm instances as you like. The examples show how to configure one.

## Examples

The operator is end-to-end tested using the definitions in the [`manifests/example/`](manifests/example/) folder. You can browse these as all options are documented in there.

* First, a namespace must be created for the configuration objects. The example uses the
[`kanidm`](manifests/example/namespace.yaml) namespace.
* You next need to configure the deployment of kanidm [using a Kanidm CRD](manifests/example/kanidm.yaml).
* Then you can [create users](manifests/example/users.yaml) or [create groups](manifests/example/groups.yaml) and any user members in them will be automatically created.
* Finally, if you want to integrate an external application, you can create an [OAuth2 endpoint](manifests/example/oauth2-client.yaml); the example shows the configuration for Forgejo (community fork of Gitea).

Each user account is created with a random password. You can reset this to a new random password by running a command in the kanidm deployment pod, i.e.:

```bash
kubectl exec -n kanidm `kubectl get pod -n kanidm -l=app.kubernetes.io/name=kanidm -o name` -- kanidmd recover-account someusername
```

However, the most important passwords are for the `admin` and `idm_admin` accounts. These
are stored in k8s secrets. You should not recover/change these, as the operator uses them to perform its operations. You can extract these by reading the secrets:

```bash
kubectl get secret -n kanidm admin-credentials -o jsonpath='{.data.password}' | base64 --decode
kubectl get secret -n kanidm idm-admin-credentials -o jsonpath='{.data.password}' | base64 --decode
```

If you accidentally recover/change these passwords, just update the secrets to the new values.

## Developing

See [docs/developing.md](docs/developing.md) for running the operator locally, the test suite, and building documentation.
