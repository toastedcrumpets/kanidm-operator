# Kanidm operator

A Kubernetes operator that deploys and manages one or more [Kanidm](https://kanidm.com/) instances.

Why use this operator? This operator lets you define the users, groups, and even
oauth endpoints in your kubernetes configuration. This means you can run your
entire Single Sign On/authentication as an ``almost'' stateless deployment. It
cannot be totally stateless, as a database is needed to store current
passwords/let users change them; however, all the configuration can be! 

# Requirements

* [cert-manager](https://cert-manager.io/): Kanidm needs to generate TLS
certificates for its operation and uses a certificate manager to generate these. 
* An ingress controller with SSL/HTTPS: A HTTPS-secured ingress to the kanidm instance is needed as the operator uses the [Kanidm Client Tools](https://kanidm.github.io/kanidm/stable/client_tools.html) to carry out configuration.

## Getting Started

First, apply the custom resource definitions:

```
kubectl apply -k github.com/toastedcrumpets/kanidm-operator/manifests/crds?ref=master
```

Then, deploy the operator:

```
kubectl apply -k github.com/toastedcrumpets/kanidm-operator/manifests/operator?ref=master
```

This will deploy the operator in the `kanidm-system` namespace. You are now ready to configure/deploy as many Kanidm instances as you like. The examples show how to configure one.

# Examples

The operator is end-to-end tested using the definitions in [manifests/examples folder](manifests/examples). You can browse these as all options are documented in there.

* First, a namespace must be created for the configuration objects. The example uses the
[`kanidm`](manifests/examples/namespace.yaml) namespace.
* You next need to configure the deployment of kanidm [using a Kanidm CRD](manifests/examples/kanidm.yaml). 
* Then you can [create users](manifests/examples/users.yaml) or [create groups](manifests/examples/groups.yaml) and any user members in them will be automatically created. 
* Finally, if you want to integrate an external application, you can create an [oauth2 endpoint](manifests/examples/oauth2-client.taml), the example shows the configuration for forgejo (community fork of gitea). 

Each user account is created with a random password. You can reset this to a new random password by running a command in the kanidm deployment pod, i.e..

```
kubectl exec -n kanidm `kubectl get pod -n kanidm -l=app.kubernetes.io/name=kanidm -o name` -- kanidmd recover-account someusername
```

However, the most important passwords are for the `admin` and `idm_admin` accounts. These
are stored in k8s secrets. You should not recover/change these, as the operator uses them to perform its operations. You can extract these by reading the secrets,

```
kubectl get secret -n kanidm admin-credentials -o jsonpath='{.data.password}' | base64 --decode
kubectl get secret -n kanidm idm-admin-credentials -o jsonpath='{.data.password}' | base64 --decode
```

If you accidentally recover/change these passwords, just update the secrets to the new values.

# Developing

To develop on the operator, you'll want to run it locally.
You need to have a k8s cluster setup with a [working kube config](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/) on your development system. You'll also need access to the kanidm deployment (e.g., https://idm.example.com).

First, install the correct version of kanidm_tools and poetry, then use poetry to setup the python environment. You can do this following the commands in the [Dockerfile](Dockerfile) for debian systems.

You're now ready to develop. You can install/reinstall the CRDS but do not install the operator as you will run this locally.

To run the operator, you will again want a command like in the end of the [Dockerfile](Dockerfile), i.e.

```
poetry run kopf run --standalone --all-namespaces 
```

## Unit tests

There is a full End-to-end set of unit tests in github actions. The action boots a KIND k8s cluster, sets up an ingress controller (nginx), cert-manager with a self-signed Certificate Authority, then installs the operator. It then deploys all the examples and checks they deployed without errors.
