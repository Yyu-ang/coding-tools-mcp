from __future__ import annotations

import json

from coding_tools_mcp.oauth import OAuthClientRegistry, OAuthConfig, create_access_token, validate_access_token


def _metadata(*, auth_method: str = "none") -> dict[str, object]:
    return {
        "redirect_uris": ["https://chatgpt.com/connector_platform_oauth_redirect"],
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "token_endpoint_auth_method": auth_method,
        "client_name": "Persistence test",
    }


def test_dynamic_client_survives_registry_restart(tmp_path) -> None:
    store = tmp_path / "oauth-clients.json"
    first = OAuthClientRegistry(store)
    registration = first.register(_metadata())
    client_id = str(registration["client_id"])

    second = OAuthClientRegistry(store)
    restored = second.get(client_id)

    assert restored is not None
    assert restored.client_id == client_id
    assert restored.accepts_redirect("https://chatgpt.com/connector_platform_oauth_redirect")


def test_confidential_client_store_contains_digest_not_plaintext_secret(tmp_path) -> None:
    store = tmp_path / "oauth-clients.json"
    first = OAuthClientRegistry(store)
    registration = first.register(_metadata(auth_method="client_secret_post"))
    client_id = str(registration["client_id"])
    client_secret = str(registration["client_secret"])

    persisted_text = store.read_text(encoding="utf-8")
    persisted = json.loads(persisted_text)
    assert client_secret not in persisted_text
    assert persisted["version"] == 1

    second = OAuthClientRegistry(store)
    assert second.authenticates(client_id, client_secret, "client_secret_post")


def test_access_token_remains_valid_after_registry_restart(tmp_path) -> None:
    store = tmp_path / "oauth-clients.json"
    first_registry = OAuthClientRegistry(store)
    registration = first_registry.register(_metadata())
    client_id = str(registration["client_id"])
    token_secret = b"stable-desktop-token-secret"
    server_url = "https://mcp.example.test"

    first_config = OAuthConfig(
        password="approval-password",
        server_url=server_url,
        token_secret=token_secret,
        registry=first_registry,
    )
    token = create_access_token(first_config, server_url, client_id=client_id)

    restarted_config = OAuthConfig(
        password="approval-password",
        server_url=server_url,
        token_secret=token_secret,
        registry=OAuthClientRegistry(store),
    )
    assert validate_access_token(token, restarted_config, server_url)
