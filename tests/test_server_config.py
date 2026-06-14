"""Unit tests for generated Kanidm server configuration."""

from jinja2 import Environment, FileSystemLoader, select_autoescape

from kanidm_operator.deploy.kanidm import parse_recover_account_password


def _render_server_toml(**variables) -> str:
    env = Environment(
        loader=FileSystemLoader("kanidm_operator/templates"),
        autoescape=select_autoescape(["toml", "yaml", "yml", "json"]),
    )
    template = env.get_template("server.toml", globals={"namespace": "kanidm", "version": "1.10.3"})
    rendered = template.render(**variables)
    configmap = __import__("yaml").safe_load(rendered)
    return configmap["data"]["server.toml"]


def test_server_toml_renders_version_two_config() -> None:
    toml = _render_server_toml(
        domain="idm.example.com",
        log_level="info",
        ldap_port=3890,
        http_port=8443,
        db_fs_type="other",
        db_arc_size=2048,
        backup_enabled=True,
        backup_schedule="0 9 * * *",
        backup_versions=7,
        trust_x_forwarded_for=True,
    )

    assert 'version = "2"' in toml
    assert "[http_client_address_info]" in toml
    assert "trust_x_forward_for" not in toml
    assert 'role = "' not in toml
    assert 'db_arc_size = 2048' in toml


def test_parse_recover_account_password_supports_log_format() -> None:
    output = 'INFO new_password: "abc123xyz"\n'
    assert parse_recover_account_password(output) == "abc123xyz"


def test_parse_recover_account_password_supports_legacy_json() -> None:
    output = 'INFO {"password":"legacy-secret"}\n'
    assert parse_recover_account_password(output) == "legacy-secret"
