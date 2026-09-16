from __future__ import annotations

import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
DESKTOP_ROOT = REPO_ROOT / "apps" / "desktop-client"
if str(DESKTOP_ROOT) not in sys.path:
    sys.path.insert(0, str(DESKTOP_ROOT))

try:
    import psutil  # noqa: F401
except ModuleNotFoundError:
    fake_psutil = types.ModuleType("psutil")

    class PsutilError(Exception):
        pass

    fake_psutil.Error = PsutilError
    fake_psutil.AccessDenied = PsutilError
    fake_psutil.CONN_LISTEN = "LISTEN"
    fake_psutil.Process = object
    fake_psutil.net_connections = lambda **_kwargs: []
    fake_psutil.process_iter = lambda *_args, **_kwargs: []
    fake_psutil.wait_procs = lambda processes, **_kwargs: (processes, [])
    sys.modules["psutil"] = fake_psutil

from mcp_desktop_client import enhanced_runtime  # noqa: E402
from mcp_desktop_client.models import build_profile  # noqa: E402


class DesktopOAuthEnhancementTests(unittest.TestCase):
    def test_dynamic_oauth_uses_per_workspace_persistent_client_store(self) -> None:
        profile = build_profile(str(REPO_ROOT), "review")
        manager = enhanced_runtime.DesktopRuntimeManager()
        environment: dict[str, str] = {}

        with tempfile.TemporaryDirectory() as temporary_directory:
            state_dir = Path(temporary_directory)
            with mock.patch.object(
                enhanced_runtime,
                "log_dir_for_profile",
                return_value=state_dir,
            ):
                manager._runtime_args(profile, environment)

        self.assertEqual(
            environment[enhanced_runtime.OAUTH_CLIENT_STORE_ENV],
            str(state_dir / "oauth-clients.json"),
        )
        self.assertNotIn(enhanced_runtime.OAUTH_CLIENT_ID_ENV, environment)

    def test_fixed_oauth_client_passes_client_id_and_redirect_uri(self) -> None:
        profile = build_profile(str(REPO_ROOT), "review")
        profile.auth.oauth_fixed_client = True
        profile.auth.oauth_client_id = "stable-client-id"
        profile.auth.oauth_redirect_uris = "https://example.test/oauth/callback"
        manager = enhanced_runtime.DesktopRuntimeManager()
        environment: dict[str, str] = {}

        with tempfile.TemporaryDirectory() as temporary_directory:
            with mock.patch.object(
                enhanced_runtime,
                "log_dir_for_profile",
                return_value=Path(temporary_directory),
            ):
                manager._runtime_args(profile, environment)

        self.assertEqual(
            environment[enhanced_runtime.OAUTH_CLIENT_ID_ENV],
            "stable-client-id",
        )
        self.assertEqual(
            environment[enhanced_runtime.OAUTH_REDIRECT_URIS_ENV],
            "https://example.test/oauth/callback",
        )
        self.assertNotIn(enhanced_runtime.OAUTH_CLIENT_SECRET_ENV, environment)

    def test_fixed_oauth_client_requires_redirect_uri(self) -> None:
        profile = build_profile(str(REPO_ROOT), "review")
        profile.auth.oauth_fixed_client = True
        profile.auth.oauth_client_id = "stable-client-id"
        profile.auth.oauth_redirect_uris = ""
        manager = enhanced_runtime.DesktopRuntimeManager()

        with tempfile.TemporaryDirectory() as temporary_directory:
            with mock.patch.object(
                enhanced_runtime,
                "log_dir_for_profile",
                return_value=Path(temporary_directory),
            ):
                with self.assertRaisesRegex(ValueError, "redirect URI"):
                    manager._runtime_args(profile, {})


class DesktopPerformanceEnhancementTests(unittest.TestCase):
    def test_stopped_profile_status_does_not_scan_all_tcp_connections(self) -> None:
        profile = build_profile(str(REPO_ROOT), "review")
        manager = enhanced_runtime.DesktopRuntimeManager()

        with (
            mock.patch.object(manager, "_read_runtime_state", return_value={}),
            mock.patch.object(manager, "_find_pid_by_port") as find_by_port,
        ):
            status = manager.status(profile)

        self.assertEqual(status.state, "stopped")
        find_by_port.assert_not_called()

    def test_saved_runtime_pid_is_checked_before_global_port_scan(self) -> None:
        profile = build_profile(str(REPO_ROOT), "review")
        manager = enhanced_runtime.DesktopRuntimeManager()
        state = {
            "runtime_pid": 4242,
            "runtime_create_time": 100.0,
        }

        with (
            mock.patch.object(manager, "_process_has_create_time", return_value=True),
            mock.patch.object(manager, "_process_matches_profile", return_value=True),
            mock.patch.object(manager, "_find_pid_by_port") as find_by_port,
        ):
            pid = manager._find_runtime_pid(profile, state=state)

        self.assertEqual(pid, 4242)
        find_by_port.assert_not_called()


if __name__ == "__main__":
    unittest.main()
