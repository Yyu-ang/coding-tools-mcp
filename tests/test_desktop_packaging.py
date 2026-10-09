"""Pure-Python packaging path checks (also run in ordinary Linux CI)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DESKTOP_ROOT = REPO_ROOT / "apps" / "desktop-client"
if str(DESKTOP_ROOT) not in sys.path:
    sys.path.insert(0, str(DESKTOP_ROOT))

from mcp_desktop_client.bundled_runtime import (  # noqa: E402
    SERVER_EXE_NAME,
    frozen_server_command,
)


class FrozenRuntimeDiscoveryTests(unittest.TestCase):
    def test_source_install_does_not_force_a_bundled_server(self) -> None:
        self.assertIsNone(frozen_server_command(frozen=False))

    def test_frozen_install_prefers_its_own_server(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            exe = root / "CodingToolsMCP.exe"
            server = root / "server" / SERVER_EXE_NAME
            server.parent.mkdir()
            server.touch()
            self.assertEqual(
                frozen_server_command(executable=exe, frozen=True),
                [str(server.resolve())],
            )

    def test_incomplete_frozen_install_never_falls_back_to_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            exe = Path(temp) / "CodingToolsMCP.exe"
            with self.assertRaisesRegex(FileNotFoundError, "Repair or reinstall"):
                frozen_server_command(executable=exe, frozen=True)


if __name__ == "__main__":
    unittest.main()
