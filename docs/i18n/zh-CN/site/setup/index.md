<a id="install-vipermesh-blender-mcp"></a>
# 安装 ViperMesh Blender MCP

Canonical page: https://openrootdev.github.io/vipermesh-blender/setup/



← ViperMesh 概览

安装 ViperMeshfor Blender。

使用 MCP 服务器和插件将 AI 客户端连接到你的本地 Blender 场景。




你需要什么

Blender 5.2 是当前已测试的发布目标。

Node.js 20 或更新版本。

支持通过 stdio 使用本地 MCP 服务器的 AI 客户端。只接受远程服务器 URL 的客户端无法直接连接到此版本。

该连接器免费并按 MIT 授权。你的 AI 客户端或模型可能单独收费。不需要 Docker 和 ViperMesh 账户。




1. 启用 Blender 插件

从最新 release 下载带版本号的插件 Python 文件或 ZIP。在 Blender 中，打开 Edit → Preferences → Add-ons → Install from Disk，选择文件并启用 ViperMesh for Blender。

打开 3D Viewport 侧边栏，选择 ViperMesh 并点击 Start Local Bridge。保持 Blender 和桥接运行。默认连接为 127.0.0.1:9876。




2. 安装本地 MCP 服务器

打包安装

下载 v1.3.0 MCPB bundle 及其 SHA-256 校验和。将其导入支持本地 MCPB 扩展的客户端。bundle 包含 Node 服务器和依赖；仍然需要 Node.js 和单独的 Blender 插件。

如果没有 MCPB importer，请将 bundle 作为 ZIP 解压到永久目录。配置你的客户端启动 node，并传入 server/index.mjs 的绝对路径。遵循 bundle 和校验和指南。

从源码构建

git clone https://github.com/OpenRootdev/vipermesh-blender.git
cd vipermesh-blender
npm install
npm run build




3. 连接你的 AI 客户端

对于源码构建，请使用构建后的入口点注册服务器一次。将示例路径替换为你自己的绝对路径：

{
  "mcpServers": {
    "vipermesh-blender": {
      "command": "node",
      "args": ["C:/absolute/path/to/vipermesh-blender/dist/public-portable-blender-mcp.js"]
    }
  }
}

配置位置和顶层键取决于客户端。请参阅客户端设置指南和你的客户端文档。客户端应为完整会话保持一个 MCP 进程存活。




4. 检查连接，然后尝试一个小编辑

让你的代理首先调用 bootstrap_vipermesh_session 并检查连接结果。从小请求开始，例如移动对象或检查它是否位于支撑物上。在信任编辑前检查生成的场景和图像。

九个顶层 MCP 工具暴露发现、场景操作、检查和 Python 回退能力。这不是托管 3D 生成模型，公开连接器不包含私有 Studio 资产库。




常见设置问题

我的客户端看不到工具

检查注册的命令和绝对文件路径。确认你的客户端支持本地 stdio MCP 服务器，并且可以启动 Node。按客户端自己的说明重新加载 MCP 连接。

工具出现了，但 Blender 无法连接

确认 Blender 已打开、插件已启用，并且 Start Local Bridge 处于活动状态。保持服务器和插件桥接端口一致。将桥接保持在 loopback；不要公开暴露它。

助手不断重启服务器

配置客户端管理一个持久子进程。为每个工具调用分别运行 npm、npx 或 tsx 会丢弃现有会话。

连接是沙箱化的吗？

不是。这是受信任的本地连接器。Python 回退可以在 Blender 内部执行代码。使用受信任的客户端并审查破坏性操作。阅读安全边界。


报告设置问题 · 面向代理的文档 · Harness Library listing

Client configuration: https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/client-setup.md
Bundle and checksums: https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/mcp-distribution.md
Security: https://github.com/OpenRootdev/vipermesh-blender/blob/main/SECURITY.md
