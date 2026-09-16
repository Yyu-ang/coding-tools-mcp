from __future__ import annotations

import os
from typing import Any

from .i18n import tr
from .models import RuntimeStatus, WorkspaceProfile
from .runtime import RuntimeManager
from .storage import log_dir_for_profile


OAUTH_CLIENT_STORE_ENV = "CODING_TOOLS_MCP_OAUTH_CLIENT_STORE"
OAUTH_CLIENT_ID_ENV = "CODING_TOOLS_MCP_OAUTH_CLIENT_ID"
OAUTH_CLIENT_SECRET_ENV = "CODING_TOOLS_MCP_OAUTH_CLIENT_SECRET"
OAUTH_REDIRECT_URIS_ENV = "CODING_TOOLS_MCP_OAUTH_REDIRECT_URIS"


class DesktopRuntimeManager(RuntimeManager):
    """Desktop-specialized runtime manager.

    The upstream manager is deliberately defensive because it also recovers
    runtimes it did not launch in the current process. On Windows,
    ``psutil.net_connections()`` is comparatively expensive. The original
    lookup checked the listening port before the already-persisted runtime
    state, so normal UI refreshes repeatedly scanned every TCP connection.

    DesktopRuntimeManager keeps the recovery behavior, but checks its own
    session/state evidence first and only falls back to a system-wide port scan
    when recovery really needs it.
    """

    def _runtime_args(self, profile: WorkspaceProfile, env: dict[str, str]) -> list[str]:
        for name in (
            OAUTH_CLIENT_STORE_ENV,
            OAUTH_CLIENT_ID_ENV,
            OAUTH_CLIENT_SECRET_ENV,
            OAUTH_REDIRECT_URIS_ENV,
        ):
            env.pop(name, None)

        args = super()._runtime_args(profile, env)
        if profile.auth.type != "oauth":
            return args

        # Keep one registry per workspace. This makes DCR registrations survive
        # GUI/server restarts without leaking one workspace's OAuth clients into
        # another workspace.
        oauth_store = log_dir_for_profile(profile.id) / "oauth-clients.json"
        env[OAUTH_CLIENT_STORE_ENV] = str(oauth_store)

        if profile.auth.oauth_fixed_client:
            client_id = profile.auth.oauth_client_id.strip()
            redirects = [
                item.strip()
                for item in profile.auth.oauth_redirect_uris.replace("\n", ",").split(",")
                if item.strip()
            ]
            if not client_id:
                raise ValueError("Fixed OAuth Client ID cannot be empty.")
            if not redirects:
                raise ValueError(
                    "Fixed OAuth mode requires at least one exact redirect URI. "
                    "Paste the callback URL shown by your MCP client."
                )
            env[OAUTH_CLIENT_ID_ENV] = client_id
            # No secret is configured intentionally: the fixed desktop client is
            # a public OAuth client protected by PKCE. The authorization password
            # remains the human approval gate on the authorize page.
            env[OAUTH_REDIRECT_URIS_ENV] = ",".join(redirects)

        return args

    def _find_runtime_pid(
        self, profile: WorkspaceProfile, *, state: dict[str, object] | None = None
    ) -> int | None:
        session = self._sessions.get(profile.id)
        if (
            session
            and session.runtime_pid is not None
            and self._process_has_create_time(session.runtime_pid, session.runtime_create_time)
            and self._process_matches_profile(session.runtime_pid, profile)
        ):
            return session.runtime_pid
        if session and session.runtime_process and session.runtime_process.poll() is None:
            process_pid = session.runtime_process.pid
            if self._process_matches_profile(process_pid, profile):
                return process_pid

        # Fast path: desktop-managed runtimes already have an atomic state file.
        # Validate that PID and command line before considering a global socket
        # table scan.
        if state is None:
            state = self._read_runtime_state(profile.id)
        runtime_pid = state.get("runtime_pid", state.get("pid"))
        runtime_create_time = state.get("runtime_create_time")
        if (
            isinstance(runtime_pid, int)
            and isinstance(runtime_create_time, (int, float))
            and self._process_has_create_time(runtime_pid, float(runtime_create_time))
            and self._process_matches_profile(runtime_pid, profile)
        ):
            return runtime_pid

        # Recovery fallback for an older state file or a runtime launched outside
        # the current desktop process. This is intentionally last because
        # psutil.net_connections(kind="tcp") is expensive on Windows.
        port_pid = self._find_pid_by_port(profile.runtime.local_port)
        if port_pid is not None and self._process_matches_profile(port_pid, profile):
            return port_pid
        return None

    def status(self, profile: WorkspaceProfile) -> RuntimeStatus:
        # A never-started/stopped desktop profile has neither a managed session
        # nor a runtime state file. Avoid a full system TCP scan merely to render
        # "Stopped" in the workspace list or after pressing Save/Refresh.
        state = self._read_runtime_state(profile.id)
        session = self._sessions.get(profile.id)
        has_live_session = bool(
            session
            and (
                session.runtime_pid is not None
                or (session.runtime_process is not None and session.runtime_process.poll() is None)
            )
        )
        if not state and not has_live_session:
            return RuntimeStatus(
                state="stopped",
                local_message=tr("RuntimeManager", "Not running"),
                public_message=tr("RuntimeManager", "Unknown"),
            )
        return super().status(profile)
