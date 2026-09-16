from __future__ import annotations

from PySide6.QtWidgets import QApplication, QCheckBox, QGroupBox, QLabel, QLineEdit, QPushButton

from . import app as app_module
from .app import MainWindow as BaseMainWindow
from .enhanced_runtime import DesktopRuntimeManager
from .models import WorkspaceProfile


class MainWindow(BaseMainWindow):
    """Desktop window with persistent OAuth and a fixed-client option."""

    def _build_auth_group(self) -> QGroupBox:
        box = super()._build_auth_group()

        self.oauth_fixed_client = QCheckBox(
            "Use fixed OAuth Client ID / 使用固定 OAuth Client ID"
        )
        self.oauth_fixed_client.setToolTip(
            "Enable this only when the MCP client lets you enter a user-defined OAuth Client ID. "
            "Automatic DCR remains the recommended default and is now persisted across restarts."
        )
        self.oauth_fixed_client.toggled.connect(self._refresh_auth_fields)

        self.oauth_client_id_label = QLabel("OAuth Client ID / 客户端 ID")
        self.oauth_client_id = QLineEdit()
        self.oauth_client_id.setPlaceholderText("coding-tools-...")

        self.oauth_redirect_uris_label = QLabel("OAuth Redirect URI / 回调地址")
        self.oauth_redirect_uris = QLineEdit()
        self.oauth_redirect_uris.setPlaceholderText(
            "Paste the exact callback URL shown by ChatGPT/your MCP client"
        )
        self.oauth_redirect_uris.setToolTip(
            "Comma-separated when more than one exact redirect URI is required."
        )

        self.auth_form.addRow(self.oauth_fixed_client)
        self.auth_form.addRow(self.oauth_client_id_label, self.oauth_client_id)
        self.auth_form.addRow(self.oauth_redirect_uris_label, self.oauth_redirect_uris)

        self.copy_oauth_client_id_button = QPushButton("Copy Client ID / 复制 Client ID")
        self.copy_oauth_client_id_button.setProperty("secondary", True)
        self.copy_oauth_client_id_button.clicked.connect(self._copy_oauth_client_id)
        oauth_actions_layout = self.oauth_actions.layout()
        if oauth_actions_layout is not None:
            oauth_actions_layout.insertWidget(1, self.copy_oauth_client_id_button)

        return box

    def _wire_live_updates(self) -> None:
        super()._wire_live_updates()
        self.oauth_fixed_client.toggled.connect(self._refresh_connection_view)
        self.oauth_client_id.textChanged.connect(self._refresh_connection_view)
        self.oauth_redirect_uris.textChanged.connect(self._refresh_connection_view)

    def _refresh_auth_fields(self, *_args: object) -> None:
        super()._refresh_auth_fields(*_args)
        is_oauth = self._combo_value(self.auth_type) == "oauth"
        fixed = is_oauth and self.oauth_fixed_client.isChecked()
        self.oauth_fixed_client.setVisible(is_oauth)
        self._set_row_visible(self.oauth_client_id_label, self.oauth_client_id, fixed)
        self._set_row_visible(
            self.oauth_redirect_uris_label,
            self.oauth_redirect_uris,
            fixed,
        )
        self.copy_oauth_client_id_button.setVisible(fixed)
        if not is_oauth:
            return
        if fixed:
            self.auth_hint.setText(
                "Fixed OAuth mode / 固定 OAuth：在 ChatGPT 或其他 MCP 客户端中选择 User-Defined OAuth Client，"
                "填入这里的 Client ID，并把客户端显示的精确 Redirect/Callback URI 粘贴到上方。"
                "授权时仍使用 Authorization password。"
            )
        else:
            self.auth_hint.setText(
                "Automatic OAuth (recommended) / 自动 OAuth（推荐）：客户端通过 DCR 自动注册。"
                "注册信息现已按 Workspace 持久化，关闭并重新打开桌面端后不会再因为注册表丢失而出现 "
                "Unknown client_id。首次授权仍使用 Authorization password。"
            )

    def _load_profile(self, profile: WorkspaceProfile) -> None:
        super()._load_profile(profile)
        self.oauth_fixed_client.setChecked(profile.auth.oauth_fixed_client)
        self.oauth_client_id.setText(profile.auth.oauth_client_id)
        self.oauth_redirect_uris.setText(profile.auth.oauth_redirect_uris)
        self._refresh_auth_fields()

    def _update_profile_from_form(self, profile: WorkspaceProfile) -> None:
        super()._update_profile_from_form(profile)
        profile.auth.oauth_fixed_client = self.oauth_fixed_client.isChecked()
        profile.auth.oauth_client_id = self.oauth_client_id.text().strip()
        profile.auth.oauth_redirect_uris = self.oauth_redirect_uris.text().strip()

    def _clear_panel(self) -> None:
        super()._clear_panel()
        if hasattr(self, "oauth_fixed_client"):
            self.oauth_fixed_client.setChecked(False)
            self.oauth_client_id.clear()
            self.oauth_redirect_uris.clear()

    def _copy_oauth_client_id(self) -> None:
        value = self.oauth_client_id.text().strip()
        if not value:
            return
        QApplication.clipboard().setText(value)
        self.statusBar().showMessage("OAuth Client ID copied / Client ID 已复制", 2500)


def main() -> int:
    # Base MainWindow deliberately constructs RuntimeManager itself. Patch the
    # module binding only for application construction so the enhanced manager
    # is used without coupling the upstream base UI to desktop-only behavior.
    original_runtime_manager = app_module.RuntimeManager
    original_main_window = app_module.MainWindow
    app_module.RuntimeManager = DesktopRuntimeManager
    app_module.MainWindow = MainWindow
    try:
        return app_module.main()
    finally:
        app_module.RuntimeManager = original_runtime_manager
        app_module.MainWindow = original_main_window
