rm manifests.tmp.yaml
kubectl kustomize manifests/crds/ >> manifests.tmp.yaml
echo "---" >> manifests.tmp.yaml
kubectl kustomize manifests/operator/ >> manifests.tmp.yaml
cat manifests.tmp.yaml | helmify ../../Personal/homelab-harvester/platform/kanidm/charts/kanidm-operator-chart
# cat manifests.tmp.yaml | helmify ../kanidm-operator-chart
