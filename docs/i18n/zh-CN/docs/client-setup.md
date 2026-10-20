<a id="mcp-client-setup"></a>
# MCP 客户端设置

<a id="what-starts-what"></a>
## 谁启动什么

ViperMesh for Blender 有两个本地连接：

1. MCP 客户端将 ViperMesh Node 服务器作为长生命周期 stdio 子进程启动。
2. Node 服务器打开并复用到 Blender 插件 `127.0.0.1:9876` 的串行化 TCP 连接。

MCP 客户端负责服务器生命周期。只需在客户端中注册服务器一次，然后使用该客户端会话中暴露的 MCP 工具。为每次工具调用分别运行一个独立的 `npm`、`npx` 或 `tsx` 命令会创建新的服务器进程，并丢弃持久连接。

对于支持本地 stdio MCP 服务器的客户端，不需要 Docker。

<a id="native-stdio-setup"></a>
## 原生 Stdio 设置

克隆、安装并构建仓库：

```bash
git clone https://github.com/OpenRootdev/vipermesh-blender.git
cd vipermesh-blender
npm install
npm run build
```

使用绝对路径指向构建后的入口点。这样可以避免依赖特定客户端的工作目录选项。

<a id="codex"></a>
### Codex

```bash
codex mcp add vipermesh-blender -- node C:/absolute/path/to/vipermesh-blender/dist/public-portable-blender-mcp.js
```

确认注册：

```bash
codex mcp list
```

如果当前任务不会重新加载 MCP 注册，请打开一个新的 Codex 任务。

<a id="json-configured-clients"></a>
### JSON 配置的客户端

Claude Desktop 等客户端和其他宿主通常接受一个命令和参数数组：

```json
{
  "mcpServers": {
    "vipermesh-blender": {
      "command": "node",
      "args": [
        "C:/absolute/path/to/vipermesh-blender/dist/public-portable-blender-mcp.js"
      ]
    }
  }
}
```

配置文件名和顶层键因客户端而异。使用该客户端当前的 MCP 文档，但保持命令本身等价。

<a id="client-compatibility"></a>
## 客户端兼容性

当客户端支持通过 stdio 使用本地 MCP 服务器，并且可以启动子进程时，它可以直接使用此版本。仅有 MCP 支持并不保证：

- 一些客户端支持本地 stdio 和远程 Streamable HTTP；
- 一些客户端只支持远程服务器 URL；
- 一些客户端要求插件、扩展或管理员策略先允许本地进程执行。

此版本仅支持 stdio。仅支持远程的客户端需要单独托管的 MCP 传输或兼容网关；它不能直接连接到 Blender 插件的 TCP 协议。

<a id="docker-mcp-toolkit"></a>
## Docker MCP Toolkit

Docker MCP Toolkit 可以集中管理容器化 MCP 服务器，并将它的 stdio 网关连接到受支持的客户端。它是可选的分发路线，不是 ViperMesh 的要求。

ViperMesh 当前未发布 Docker MCP Catalog 条目。出于本地安全考虑，Blender 插件也仍然仅限 loopback。容器必须可靠访问该主机 loopback 服务，而这会随 Docker 主机、网络模式和客户端环境变化。

因此，原生 stdio 是目前受支持的设置。不要仅为了让容器连接而把 Blender 桥接暴露在公共接口上。Docker Toolkit 指南会在一次端到端 Windows、macOS 和 Linux 连接测试定义出安全配置后，才提升为受支持路径。

官方参考：

- [MCP transports](https://modelcontextprotocol.io/specification/latest/basic/transports)
- [Docker MCP Toolkit](https://docs.docker.com/ai/mcp-catalog-and-toolkit/)

<a id="verify-the-session"></a>
## 验证会话

1. 启动 Blender 和 ViperMesh 本地桥接。
2. 在已配置的 MCP 客户端中打开新会话。
3. 调用 `bootstrap_vipermesh_session`。
4. 确认 `connection.connected` 为 `true`，且 `sessionModel` 为 `persistent`。
5. 进行两次轻量检查调用。它们应复用一个 MCP 进程和一个 Blender 客户端，而不是启动新的 shell 命令。
