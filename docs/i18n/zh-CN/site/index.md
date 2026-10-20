<a id="vipermesh-blender-mcp-server-and-addon"></a>
# ViperMesh：Blender MCP 服务器和插件

> 免费、开源、本地的 AI 辅助，用于 Blender 场景编辑、检查和可复用 3D 操作。

Canonical page: https://openrootdev.github.io/vipermesh-blender/
Repository: https://github.com/OpenRootdev/vipermesh-blender
License: MIT，NOTICE.md 中包含上游署名。

ViperMesh 使用两个本地部分。兼容的 AI 客户端通过 stdio 启动一个持久 Node MCP 进程。该进程通过串行化 loopback TCP 桥接连接到 Blender 插件，默认地址为 127.0.0.1:9876。

现成操作覆盖场景排列、材质、灯光、相机、几何和 UV 准备、绑定、权重、动画操作、导出和诊断。九个顶层 MCP 工具暴露这些能力。代理应首先调用 bootstrap_vipermesh_session。Python 执行仍可用于自定义工作。

场景检查和视觉检查帮助代理修复其工作。更少的生成 token、更快的工作和更好的结果是目标，不是普遍保证。结果取决于模型、场景和任务。

该连接器不是托管生成模型。它不捆绑 AI 模型、云路由、私有 Studio 资产库、身份验证或计费。不需要 Docker 和 ViperMesh 账户；模型访问可能单独收费。它是受信任的本地连接器，不是沙箱。

<a id="install"></a>
## 安装

Blender 5.2 是当前已测试的发布目标。需要 Node.js 20+ 以及能够使用本地 stdio MCP 的客户端。启用单独的 Blender 插件并启动本地桥接。在受支持的客户端中导入 MCPB bundle，或构建源码并注册构建后的入口点。为整个会话保持一个进程运行。

- [安装和故障排查](https://openrootdev.github.io/vipermesh-blender/setup/index.md)
- [客户端配置](https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/client-setup.md)
- [Release bundles](https://github.com/OpenRootdev/vipermesh-blender/releases)
- [连接器手册](https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/portable-blender-mcp.md)
- [代理技能](https://github.com/OpenRootdev/vipermesh-blender/blob/main/skills/using-vipermesh-blender/SKILL.md)
- [安全边界](https://github.com/OpenRootdev/vipermesh-blender/blob/main/SECURITY.md)
- [图示概览](https://openrootdev.github.io/vipermesh-blender/#overview)
- [Harness Library](https://openrootdev.github.io/harness-library/harnesses/vipermesh-blender/)
