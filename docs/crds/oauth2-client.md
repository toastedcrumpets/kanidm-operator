# OAuth2 client custom resource

Creates a Kanidm OAuth2 resource server client and stores its credentials in a Kubernetes secret.

```yaml
apiVersion: kanidm.github.io/v1alpha1
kind: OAuth2Client
metadata:
  name: forgejo-oauth
  namespace: kanidm
spec:
  kanidmName: kanidm-instance
  name: forgejo
  displayName: Forgejo
  origin: https://git.example.com
  prefer-short-username: true
  enable-pkce: true
  callback-url: https://git.example.com/user/oauth2/callback
  scope-map:
    group: git-users
    scopes:
      - openid
      - email
  claim-map:
    claim: app_role
    groups:
      admins: Admin
  secret:
    labels:
      secret-kind: oauth2-client
    annotations: {}
```

## Fields

| Field | Description |
|-------|-------------|
| `name` | OAuth2 client ID in Kanidm |
| `displayName` | Display name shown during consent |
| `origin` | Allowed origin URL |
| `prefer-short-username` | Enable short username preference (useful for Forgejo/Gitea) |
| `enable-pkce` | Defaults to enabled; set `false` to disable PKCE |
| `callback-url` | Sets the OAuth2 landing URL |
| `scope-map` | Maps a group to OAuth2 scopes |
| `claim-map` | Maps groups to custom token claims |
| `secret.labels` / `secret.annotations` | Extra metadata on the generated secret |

## Generated secret

The operator creates `{spec.name}-oauth2-credentials` with:

- `key` — client ID
- `secret` — client secret from Kanidm

## Examples

- [`manifests/example/oauth2-client.yaml`](https://github.com/juniorfoo/kanidm-operator/blob/master/manifests/example/oauth2-client.yaml) — Forgejo
- [`manifests/example/oauth2-client-grafana.yaml`](https://github.com/juniorfoo/kanidm-operator/blob/master/manifests/example/oauth2-client-grafana.yaml) — Grafana with claim mapping
