from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from coding_tools_mcp.oauth import (
    OAUTH_CLIENT_STORE_ENV,
    OAuthClientRegistry,
    OAuthConfig,
    create_access_token,
    validate_access_token,
)


REDIRECT_URI = "https://chatgpt.com/connector_platform_oauth_redirect"


def _metadata(*, auth_method: str = "none") -> dict[str, object]:
    return {
        "redirect_uris": [REDIRECT_URI],
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "token_endpoint_auth_method": auth_method,
        "client_name": "Persistence test",
    }


class OAuthClientPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary_directory.cleanup)
        self.store = Path(self._temporary_directory.name) / "oauth-clients.json"

    def test_dynamic_client_survives_registry_restart(self) -> None:
        first = OAuthClientRegistry(self.store)
        registration = first.register(_metadata())
        client_id = str(registration["client_id"])

        second = OAuthClientRegistry(self.store)
        restored = second.get(client_id)

        self.assertIsNotNone(restored)
        assert restored is not None
        self.assertEqual(restored.client_id, client_id)
        self.assertTrue(restored.accepts_redirect(REDIRECT_URI))

    def test_confidential_client_store_contains_digest_not_plaintext_secret(self) -> None:
        first = OAuthClientRegistry(self.store)
        registration = first.register(_metadata(auth_method="client_secret_post"))
        client_id = str(registration["client_id"])
        client_secret = str(registration["client_secret"])

        persisted_text = self.store.read_text(encoding="utf-8")
        persisted = json.loads(persisted_text)
        self.assertNotIn(client_secret, persisted_text)
        self.assertEqual(persisted["version"], 1)

        second = OAuthClientRegistry(self.store)
        self.assertTrue(second.authenticates(client_id, client_secret, "client_secret_post"))

    def test_access_token_remains_valid_after_registry_restart(self) -> None:
        first_registry = OAuthClientRegistry(self.store)
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
            registry=OAuthClientRegistry(self.store),
        )
        self.assertTrue(validate_access_token(token, restarted_config, server_url))

    def test_registry_store_can_be_selected_via_environment(self) -> None:
        with mock.patch.dict(
            os.environ,
            {OAUTH_CLIENT_STORE_ENV: str(self.store)},
            clear=False,
        ):
            first = OAuthClientRegistry()
            registration = first.register(_metadata())
            client_id = str(registration["client_id"])
            second = OAuthClientRegistry()

        self.assertIsNotNone(second.get(client_id))


if __name__ == "__main__":
    unittest.main()
