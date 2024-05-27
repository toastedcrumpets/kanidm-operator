# Kanidm operator

Kubernetes operator that allows you to create groups, OAuth clients, Accounts and more for kanidm


## Getting Started

First, apply the custom resource definitions to your cluster using

`kubectl apply -k github.com/toastedcrumpets/kanidm-operator/manifests/crds?ref=master`

This will apply the latest `CustomResourceDefinition` for the operator. Then, deploy the operator with

`kubectl apply -k github.com/toastedcrumpets/kanidm-operator/manifests/operator?ref=master`

Which will deploy the operator in the `kanidm-system` namespace.

To deploy kanidm using the operator, create a new `Kanidm` resource, following the examples at https://github.com/sbordeyne/kanidm-operator/tree/master/example

```yaml
apiVersion: v1alpha1
kind: Kanidm
metadata:
  name: kanidm
  namespace: kanidm
spec:
  version: 1.2.0
  database:
    fsType: other
    storageClass: nfs-client
    storageSize: 1Gi
  domain: idm.example.com
  certificate:
    issuer: cluster-issuer
  logLevel: info
  backup:
    enabled: true
    schedule: "0 9 * * *"
    versions: 7
    storageClass: nfs-client
    storageSize: 7Gi
  webPort: 8443
  ldapPort: 3890
  highAvailability:
    enabled: false
    replicas: 1
```

If the operator is running, and kanidm is deployed, you can then use the operator to create groups, accounts, service accounts, OAuth2 clients and more using the provided CRDs. Note that if you deployed kanidm without the operator, it will not be able to access the server (you could trick it by renaming your service `kanidm-svc` and adding both the `admin` and `idm-admin` secrets in the `kanidm-system` namespace)

# Developing

To develop with the operator, you'll want to run it locally.
You need to have a k8s cluster setup with a [working kube config](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/) on your development system. You'll also need access to the kanidm deployment (e.g., https://idm.example.com).

First, install the correct version of kanidm_tools and poetry, then use poetry to setup the python environment. You can do this following the commands in the [Dockerfile](Dockerfile) for debian systems.

You're now ready to develop. You can install/reinstall the CRDS but do not install the operator as you will run this locally.

To run the operator, you will again want a command like in the end of the [Dockerfile](Dockerfile), i.e.

```
poetry run -vvv kopf run --standalone --all-namespaces 
```
