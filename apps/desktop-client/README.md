# MCP 桌面客户端

这是 `coding-tools-mcp` 的 Python 桌面客户端 MVP，核心目标是让研发同学用一个中文界面完成：

- 管理多个 Workspace
- 配置公网暴露地址，当前支持外部托管的 FRP 和由客户端管理的 Cloudflare
- 配置 OAuth / Bearer / NoAuth
- 启动和停止本地 MCP 运行时
- 查看运行日志和当前入口地址
- 直接复制 ChatGPT 自定义 MCP 应用需要填写的核心字段

## 运行

```bash
python -m pip install -e ".[desktop]"
coding-tools-mcp-desktop
```

也可以继续从源码直接运行：

```bash
python apps/desktop-client/main.py
```

## 依赖

- Python 3.11+
- PySide6
- psutil
- `uvx` 或 `coding-tools-mcp` 已在 PATH 中可用

## 语言

客户端首次启动时跟随系统语言，目前内置：

- English
- 简体中文

可以在左侧语言选择框中即时切换，选择结果会通过 Qt 设置持久化。系统语言不受支持时默认使用英文。

更新界面文本后，使用 PySide6 Linguist 工具刷新并检查翻译目录：

```bash
make desktop-i18n-update
make desktop-i18n-release
python scripts/check_desktop_i18n.py
```

## ChatGPT 接入

认证方式选择 `oauth` 后，默认使用 OAuth Dynamic Client Registration（DCR）。每个 Workspace 的动态 OAuth 客户端注册表会持久化到桌面客户端私有状态目录，因此关闭桌面端或重启 MCP 服务后，已经注册的 `client_id` 不会仅因为进程退出而丢失，已有连接也不会再因这一原因出现 `Unknown client_id`。

界面中的 **Authorization password** 是授权页面的人机口令，仍会随 Workspace 持久化。首次授权时输入该口令即可。

如果 ChatGPT 或其他 MCP 客户端支持 **User-Defined OAuth Client**，也可以启用 **Use fixed OAuth Client ID**：

1. 保留界面生成的 Client ID，或改成你自己的固定值；
2. 在客户端创建 OAuth 连接时填写该 Client ID；
3. 将客户端显示的精确 Redirect/Callback URI 粘贴回桌面端的 `OAuth Redirect URI`；
4. 保存配置并重启该 Workspace 的 MCP Runtime；
5. 授权页面继续使用 Authorization password。

固定 Client ID 模式默认使用 public OAuth client + PKCE，不要求额外保存 Client Secret。Redirect URI 按 OAuth 规范进行精确匹配；如果客户端为每个连接生成不同 callback URL，应粘贴该连接实际显示的 URI，或者继续使用默认的持久化 DCR 模式。

如果你使用 FRP，请把 Workspace、本地端口、FRP 子域名和服务器域名配好，复制界面生成的 FRP 片段，并在同一台主机上的 `frpc` 配置中应用它。桌面客户端只管理本地 MCP 运行时，不会替你启动或重载 `frpc`；界面显示的 FRP 公网地址也需要外部 `frpc` 正常运行后才可访问。

如果你使用 Cloudflare，有两种模式：

- 临时隧道：使用 `cloudflared tunnel --url`，启动后自动分配一个 `trycloudflare.com` 公网地址
- 固定域名：使用 `Tunnel Token` 启动命名隧道，并在界面里填写固定公网地址

## 性能说明

桌面端启动/停止 Runtime 继续在后台 `QThread` 中执行；状态刷新优先读取桌面端已经保存的 Runtime PID/state，仅在恢复未知进程时才回退到全系统 TCP 连接扫描。这样可以避免 Windows 上按钮操作、保存配置或刷新 Workspace 时反复调用较重的 `psutil.net_connections()`。

## 当前限制

- FRP 当前是外部托管模式；客户端只生成配置片段，不管理 `frpc` 进程
- `Ngrok`、`Dev Tunnel` 还没有实现真实隧道启动能力
- Cloudflare 命名隧道模式依赖你提前在 Cloudflare 仪表盘里配置好 tunnel 和 hostname
- Cloudflare 命名隧道模式下，本地服务地址需要和 Cloudflare Tunnel 的 ingress 目标一致，通常是 `http://127.0.0.1:<本地端口>`


## Windows x64 安装版（本 Fork 独立发行）

Windows 安装版采用 **PyInstaller onedir GUI + 内置 MCP Server + Inno Setup**。
用户无需额外安装 Python、Conda 或 uv。打包代码仅在
[packaging/](packaging/) 中维护，核心 MCP Server、上游 Python 包发布流程不受影响。

- 安装包：CodingToolsMCP_Desktop_<版本>_x64_Setup.exe，按当前用户安装，创建开始菜单快捷方式。
- 免安装包：CodingToolsMCP_Desktop_<版本>_x64_Portable.zip，解压后运行 CodingToolsMCP.exe。
- 两种发行形式都包含 server/coding-tools-mcp-server.exe；普通用户无需单独安装 Server。
- 应用启动后，默认优先运行内置 Server。只有在 Workspace 显式配置了自定义运行命令时才使用外部程序。
- 未捆绑 cloudflared 或 frpc；需要隧道的用户应自行安装/配置对应工具，FRP 保持外部管理模式。
- 配置、日志及 OAuth 注册记录位于用户主目录的 .coding-tools-mcp-desktop，升级及卸载程序不会清理该目录。

### 本地构建（Windows PowerShell）

在仓库根目录执行：

~~~powershell
python -m pip install -e ".[desktop]"
python -m pip install "pyinstaller>=6.15,<7"
# 另行安装 Inno Setup，并确保 ISCC.exe 可以被找到
.\apps\desktop-client\packaging\build-windows.ps1
~~~

构建产物位于 dist/desktop-release/。如仅需便携版，使用 -SkipInstaller 参数。
构建前检查 apps/desktop-client/packaging/desktop-version.txt；
其前三段必须与 pyproject.toml 的 Python 包版本一致。

### GitHub Actions

[desktop-release.yml](../../.github/workflows/desktop-release.yml) 是独立工作流：

1. PR 修改桌面端、核心运行时或打包配置时，Windows Runner 自动构建、执行桌面回归测试并验证两种发行形式；
2. workflow_dispatch 可手动构建并提供 Actions artifact，不创建 GitHub Release；
3. 仅将 desktop-v0.5.0.1 这样的**独立桌面标签**推送到本 Fork，且与 desktop-version.txt 一致，才会在 **本 Fork** 创建 GitHub Release；
4. 不使用 v* 上游 Python/npm 发布标签，因此不会触发原 release.yml 的 PyPI/npm 发行。

当前生成的安装程序未进行代码签名。公开下载时可能出现 Windows SmartScreen 提示。
若准备长期发行，可后续通过私有 CI Secret 接入受信任的代码签名证书，勿提交私钥。

### 安装和更新注意事项

升级前先在界面中停止当前 Workspace 的 MCP Runtime，再退出桌面客户端；
安装器可以关闭占用文件的 GUI，但不能保证安全停止所有自定义启动的子进程。
卸载只移除安装目录，不会删除用户配置和 OAuth 凭据。
