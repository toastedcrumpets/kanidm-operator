# Kanidm operator

Kubernetes operator that deploys and manages one or more [Kanidm](https://kanidm.com/) instances.

While Kanidm requires some backing storage to allow users to change their
passwords, this operator lets you define the users, groups, and even oauth
endpoints using CRDs. This means you can run your entire Single Sign On instance as an almost stateless deployment.

# Requirements

Your kubernetes cluster must have [cert-manager](https://cert-manager.io/)
installed and configured, as kanidm needs to generate TLS certificates for its
operation. In addition, you will need to setup a HTTPS-secured ingress for the
kanidm instance (perhaps using letsencrypt with cert-manager), as the operator
will use this ingress (and verify its certificate) to carry out changes in
user/group/config etc.

## Getting Started

First, apply the custom resource definitions to your cluster using

`kubectl apply -k github.com/toastedcrumpets/kanidm-operator/manifests/crds?ref=master`

This will apply the latest `CustomResourceDefinition` for the operator. Then, deploy the operator with

`kubectl apply -k github.com/toastedcrumpets/kanidm-operator/manifests/operator?ref=master`

Which will deploy the operator in the `kanidm-system` namespace.

# Examples

The operator is tested using the definitions in [manifests/examples](manifests/examples). These show an example deployment of kanidm including creation of a user, a group, and an oauth2 endpoint for forgejo (community fork of gitea).

# Developing

To develop on the operator, you'll want to run it locally.
You need to have a k8s cluster setup with a [working kube config](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/) on your development system. You'll also need access to the kanidm deployment (e.g., https://idm.example.com).

First, install the correct version of kanidm_tools and poetry, then use poetry to setup the python environment. You can do this following the commands in the [Dockerfile](Dockerfile) for debian systems.

You're now ready to develop. You can install/reinstall the CRDS but do not install the operator as you will run this locally.

To run the operator, you will again want a command like in the end of the [Dockerfile](Dockerfile), i.e.

```
poetry run -vvv kopf run --standalone --all-namespaces 
```

## Unit tests

There is a full End-to-end set of unit tests in github actions. The action boots a KIND k8s cluster, sets up an ingress controller (nginx), cert-manager with a self-signed Certificate Authority, then installs the operator. It then deploys all the examples and checks they deployed without errors.