<a id="mcp-distribution"></a>
# MCP 分发

ViperMesh for Blender 作为本地 stdio 连接器发布。它不托管 Blender、不提供 AI 模型，也不包含私有的 ViperMesh Studio 及其完整的已基准测试 harness。

<a id="published-listings"></a>
## 已发布列表

- [Smithery: ker102/vipermesh-blender](https://smithery.ai/servers/ker102/vipermesh-blender)
- [Official MCP Registry: io.github.Ker102/vipermesh-blender](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.Ker102/vipermesh-blender)
- [GitHub release v1.3.0](https://github.com/OpenRootdev/vipermesh-blender/releases/tag/v1.3.0)

官方注册表托管元数据。MCPB 包托管在 GitHub release 中。Smithery 的列表也包含相同 bundle，以及从打包服务器发现的九个 MCP 工具 schema。

<a id="bundle-setup"></a>
## Bundle 设置

1. 使用[主安装指南](../README.md#install)安装并启用 Blender 插件。
2. 下载 [vipermesh-blender-1.3.0.mcpb](https://github.com/OpenRootdev/vipermesh-blender/releases/download/v1.3.0/vipermesh-blender-1.3.0.mcpb)
   及其 [SHA-256 file](https://github.com/OpenRootdev/vipermesh-blender/releases/download/v1.3.0/vipermesh-blender-1.3.0.mcpb.sha256)。
3. 按照该客户端的本地扩展说明，将 bundle 导入支持 MCPB 的客户端。bundle 的启动配置需要 Node.js。除非你的插件使用不同端口，否则保持桥接端口为 `9876`。
4. 启动本地 Blender 桥接，然后从 AI 客户端调用 `bootstrap_vipermesh_session` 并检查连接结果。

没有 MCPB 导入功能的客户端可以使用[源码安装](client-setup.md)。或者，MCPB 是一个 ZIP 归档：将其解压到永久目录，并注册 `node`，把 `server/index.mjs` 的绝对路径作为它的参数。解压后的包包含运行时依赖和本地指导；不需要 `npm install`。将它作为持久 stdio 子进程启动一次，而不是每个 Blender 操作启动一次。

桥接保持在 `127.0.0.1`。仅支持远程的客户端不能直接使用此本地连接器。不要为了让它们连接而公开暴露 Blender 的桥接。

<a id="release-integrity-and-validation"></a>
## 发布完整性和验证

版本 `1.3.0` 构建自源提交
`781700be4f0fb32b135d3f5cb7da012ce8fc4abd`。

Bundle SHA-256：

```text
45f8cee90540e9f906b8e817efb6fa0a1302f8dba515522dc3682d328a90206c
```

Source TypeScript 和一致性检查、插件 Python 语法、package-schema 验证、MCP 初始化、九工具发现以及本地指导查找均已通过。注册表发布前，已按此校验和检查 release 下载。

这些包检查并不能证明每个客户端的实时 Blender 兼容性。此 bundle 的实时场景测试和端到端 MCPB 安装测试仍待完成。请在一次性场景上测试，审查破坏性操作，并遵循[安全指南](../SECURITY.md)。

<a id="maintainer-notes"></a>
## 维护者说明

已发布的注册表元数据跟踪在 [server.json](../../../../server.json) 中。对于新 release，请重新构建并验证 bundle，上传其精确字节和校验和到 release，然后在发布元数据前一并更新版本、源提交、下载 URL 和哈希。

MCPB manifest 会列出工具名称。Smithery 发布还需要来自打包服务器的完整 `tools/list` schema；仅有名称不能满足其 server-card 验证。保持这些 schema 与 release 一致，而不是臆造或丢弃工具定义。
