<div align="center">

<!-- i18n:languages:start -->
[English](../../../README.md) | [Español](../es/README.md) | [简体中文](../zh-CN/README.md) | [Français](../fr/README.md) | [日本語](../ja/README.md) | [Deutsch](../de/README.md) | [Português (Brasil)](../pt-BR/README.md)
<!-- i18n:languages:end -->

<a href="https://openrootdev.github.io/vipermesh-blender/"><img src="../../../site/assets/brand-mark.png" alt="ViperMesh 标志" width="104" height="104"></a>

<h1>ViperMesh for Blender</h1>
<p>面向 AI 代理的开源 Blender MCP 服务器和插件。</p>

[![CI](https://github.com/OpenRootdev/vipermesh-blender/actions/workflows/ci.yml/badge.svg)](https://github.com/OpenRootdev/vipermesh-blender/actions/workflows/ci.yml)
[![GitHub release](https://img.shields.io/github/v/release/Ker102/vipermesh-blender?display_name=tag)](https://github.com/OpenRootdev/vipermesh-blender/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](../../../LICENSE)
[![MCP](https://img.shields.io/badge/Model_Context_Protocol-server-1f6feb)](https://modelcontextprotocol.io/)

**为 Blender 提供 AI 辅助，减少代码，减少等待。**

为更快的场景编辑、更少的 AI token 和更充分检查的结果而设计。

<p>
<a href="https://github.com/OpenRootdev/vipermesh-blender/releases/latest"><img src="../../../site/assets/readme-download.svg" alt="下载 Blender 插件" width="240" height="44"></a>
<a href="docs/client-setup.md"><img src="../../../site/assets/readme-setup.svg" alt="设置指南" width="160" height="44"></a>
</p>

[项目概览和设置](https://openrootdev.github.io/vipermesh-blender/)
| [ViperMesh Studio waitlist](https://vipermesh-studio.vercel.app/waitlist)

</div>

---

ViperMesh for Blender 是一个免费的开源 **Blender MCP server and addon**，可让兼容的 AI 助手在你的 Blender 场景中工作。它面向希望获得 3D 场景创建和编辑帮助的 Blender 艺术家、爱好者和游戏创作者，而不是另一个编码项目。

**目标：更快的 AI 辅助工作、更少的 AI token，以及更充分检查的结果。**
你的助手可以获得即用型 Blender 操作，而不必为许多常见编辑重新编写 Python 代码。你继续在 Blender 中工作，并决定希望助手协助什么。

<a id="watch-the-overview"></a>
## 观看概览

[![观看 ViperMesh for Blender 概览](../../../site/assets/connector-overview-poster.png)](https://openrootdev.github.io/vipermesh-blender/#overview)

[观看 72 秒视频](https://openrootdev.github.io/vipermesh-blender/#overview)
或[下载 MP4](https://openrootdev.github.io/vipermesh-blender/assets/connector-overview.mp4)。
了解你的 AI 客户端如何使用现成的 Blender 操作、为什么更少的生成代码会有帮助，以及如何开始。这是一段无声图示概览，不是计时基准录制。GitHub 的 README 会链接到可播放视频。

<a id="why-vipermesh-for-blender"></a>
## 为什么选择 ViperMesh for Blender？

| 你关心的事项 | ViperMesh 如何提供帮助 |
| --- | --- |
| 更少 AI 用量 | 可复用操作会减少助手在已覆盖任务中需要生成的 Blender 代码。 |
| 更少等待 | 连接会保持打开，相关操作可以一起运行，而不是每一步都重复设置。 |
| 检查更充分的场景 | 内置检查帮助识别悬空对象、错误朝向和间隙问题；助手可以检查图像并修复错误。 |
| 更方便你的助手 | 可发现的工具和简洁指导说明有哪些操作可用，以及如何使用它们。 |
| 留出自定义空间 | 当你的请求需要现成工具未覆盖的内容时，助手仍可编写 Python。 |

AI token 是模型读取和写入的文本单位。生成更少代码可以减少 AI 用量，但总 token、成本和耗时还取决于你的模型和任务。场景检查有助于正确性；它们不保证结果美观或完全无误。

<a id="one-reference-two-blender-workflows"></a>
## 一个参考，两种 Blender 工作流

<p align="center">
<a href="../../../site/assets/scandinavian-entryway-comparison.png"><img src="../../../site/assets/scandinavian-entryway-comparison.png" alt="历史场景对比：左侧为参考图像，中间为 ViperMesh MCP Blender viewport，右侧为原始 BlenderMCP viewport" width="960"></a>
</p>

一次历史图像重建测试，使用 ViperMesh Blender MCP harness 和可用资产。只有中间标题被重新标注；参考图和两个场景截图未改动。这是一个示例，不保证每次结果。公开插件不捆绑私有 Studio 资产库。

[阅读 Blender MCP 案例研究，第一部分](https://kristoferjussmann.me/case-studies/vipermesh/)
| [打开全尺寸对比图](../../../site/assets/scandinavian-entryway-comparison.png)
| [图像完整性记录](../../../site/assets/scandinavian-entryway-comparison.provenance.json)

<a id="what-can-it-help-with"></a>
## 它能帮什么？

- 在场景中构建、移动、复制和排列对象。
- 柔化边缘、调整材质、设置相机并改变灯光。
- 检查对象是否位于其支撑物上，或是否留出足够空间。
- 协助网格清理、重拓扑、UV 准备、绑定和权重。
- 处理动画设置、准备导出并检查结果。

例如，你可以这样请求助手：

> Move the basket under the right side of the table, without intersecting its legs.

> Soften the sharp edges on this furniture, keeping its overall shape.

> Check this scene for unsupported objects, then show me what needs fixing.

这些是请求示例，不是预置场景模板。对于工具覆盖的操作，你不需要自己编写 Blender Python。

<a id="how-is-it-different-from-the-original-blendermcp"></a>
## 它与原始 BlenderMCP 有何不同？

ViperMesh 基于 Siddharth Ahuja 的原始 [BlenderMCP project](https://github.com/ahujasid/mcp-for-blender) 构建，该项目现在名为 MCP for Blender。主要区别是它强调广泛的现成编辑操作、可复用工作流和场景检查，而不是依赖为常见编辑新生成 Python。

两个项目都可以检查场景并运行自定义 Python。原始项目也提供资产和生成集成。ViperMesh 的目标是让日常场景操作更节省 token、更快、更便于助手使用且更易验证。这并不是声称它在每个任务上都胜出，也不是声称公开连接器包含 ViperMesh Studio 的每项功能。

[网站安装指南](https://openrootdev.github.io/vipermesh-blender/setup/) · [Harness Library listing](https://openrootdev.github.io/harness-library/harnesses/vipermesh-blender/)

<a id="requirements"></a>
## 要求

- Blender 5.2，用于当前已测试的发布目标
- Node.js 20 或更新版本
- 支持 stdio 服务器的 MCP 兼容客户端

MCP 是 Model Context Protocol 的缩写，是一种连接标准，可让 AI 助手使用另一个应用中的工具。你需要支持这些连接的 AI 应用；仅安装插件不会向 Blender 添加 AI 模型。

<a id="install"></a>
## 安装

<a id="1-install-the-blender-addon"></a>
### 1. 安装 Blender 插件

从 [latest release](https://github.com/OpenRootdev/vipermesh-blender/releases/latest) 下载带版本号的插件 `.py` 或插件 `.zip`。在 Blender 中：

1. 打开 **Edit > Preferences > Add-ons**。
2. 选择 **Install from Disk**，并选择下载的 Python 文件。
3. 启用 **ViperMesh for Blender**。
4. 打开 3D Viewport 侧边栏，选择 **ViperMesh**，并点击 **Start Local Bridge**。

在完整代理会话期间保持桥接运行。

<a id="2-install-the-mcp-server"></a>
### 2. 安装 MCP 服务器

**打包选项：** 下载
[`v1.3.0` MCPB bundle](https://github.com/OpenRootdev/vipermesh-blender/releases/download/v1.3.0/vipermesh-blender-1.3.0.mcpb)
并将其导入支持本地 MCPB 扩展的客户端。它包含 Node 服务器及其依赖，因此你不需要克隆或构建仓库。仍然需要 Node.js 和单独启用的 Blender 插件。

该连接器也列在
[Smithery](https://smithery.ai/servers/ker102/vipermesh-blender) 和
[official MCP Registry](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.Ker102/vipermesh-blender)。
这些列表分发的是本地连接器，不是托管的 Blender 服务。请参阅[分发和 bundle 设置](docs/mcp-distribution.md)，了解校验和、手动解压选项和当前验证限制。

**源码选项：** 在 npm 包发布之前，请克隆并构建它：

```bash
git clone https://github.com/OpenRootdev/vipermesh-blender.git
cd vipermesh-blender
npm install
npm run build
```

<a id="3-connect-your-ai-assistant"></a>
### 3. 连接你的 AI 助手

使用 MCPB 导入时，客户端会从 bundle 读取其启动配置。对于源码选项，请从绝对路径使用构建后的入口点：

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

通过 MCP 客户端启动此命令一次。不要为每个 Blender 操作再次调用 `npm`、`npx` 或 `tsx`。请参阅 [MCP 客户端设置](docs/client-setup.md)，了解 Codex、JSON 配置客户端、兼容性和可选 Docker MCP Toolkit 路线。

<a id="technical-details"></a>
## 技术细节

以下章节用于设置或开发 AI 连接。Blender 用户可以从安装步骤和上面的示例请求开始。

<a id="connection-model"></a>
### 连接模型

```text
MCP-compatible AI assistant
        |
        | stdio, one long-lived process
        v
ViperMesh MCP server
        |
        | serialized loopback connection
        v
ViperMesh Blender addon (127.0.0.1:9876)
        |
        v
Blender scene
```

MCP 服务器不会打开网络监听器。Blender 插件默认监听 loopback，并在 ViperMesh 侧边栏中报告 **Stopped**、**Ready**、**Agent connected** 或 **Error**。

<a id="first-agent-calls"></a>
### 首次代理调用

1. 调用 `bootstrap_vipermesh_session`。
2. 使用 `call_blender_tool(name="get_scene_info")` 检查场景。
3. 使用 `search_3d_guidance` 搜索任务指导。
4. 使用 `list_blender_tools` 只发现相关能力。
5. 构建、检查并修复，然后 finalize 并保存。

公开 MCP 表面包括：

- `bootstrap_vipermesh_session`
- `check_blender_connection`
- `list_blender_tools`
- `call_blender_tool`
- `call_blender_tool_batch`
- `run_blender_scene_stage`
- `get_blender_agent_context`
- `search_3d_guidance`
- `get_3d_guidance_document`

阅读[完整连接器手册](docs/portable-blender-mcp.md)，了解请求形状、批处理规则、分阶段工作流、本地工具技能和故障排查。仓库还附带一个可安装的 [`using-vipermesh-blender` agent skill](skills/using-vipermesh-blender/SKILL.md)。

<a id="security"></a>
## 安全

此连接器用于受信任的本地工作站。`execute_code` 可以在 Blender 中运行任意 Python。只连接受信任的 MCP 客户端，将桥接保持在 loopback，并审查高影响或破坏性操作。

请参阅 [SECURITY.md](SECURITY.md)，了解信任边界和私有漏洞报告流程。

<a id="public-connector-scope"></a>
## 公开连接器范围

此仓库包含开源 Blender 插件、便携 MCP 服务器、便携公开工具技能和连接器测试。它不包含 ViperMesh application、authentication、billing、private prompts、private RAG data、cloud model routing、private assets、raw benchmark traces 或 private evaluation datasets。图示对比是单独提供的公开证据，不是捆绑的资产库。

该连接器不捆绑商业 3D 生成提供商。后续可以通过提供商中立的已认证服务添加神经生成，而不在 Blender 中嵌入第三方凭据。

<a id="frequently-asked-questions"></a>
## 常见问题

<a id="do-i-need-a-paid-vipermesh-account"></a>
### 我需要付费 ViperMesh 账户吗？

不需要。公开插件和本地连接可以免费使用，不需要 ViperMesh 账户。你的 AI 应用或模型提供商可能会单独收费。插件不包含免费 AI 模型访问。

<a id="do-i-need-to-be-a-programmer"></a>
### 我需要会编程吗？

对于已覆盖的 Blender 编辑，你不需要编写 Python。初始设置仍涉及安装插件并连接兼容的 AI 应用。在支持 MCPB 的客户端中使用 MCPB bundle，或使用提供的命令从源码构建。单独启用的 Blender 桥接和客户端设置意味着这并非适用于每个环境的一键安装。

<a id="does-vipermesh-replace-execute_code"></a>
### ViperMesh 会替代 `execute_code` 吗？

不会。它通过提供结构化操作减少不必要的生成式 Blender Python，但仍保留 `execute_code`，用于自定义几何、程序化效果、非常规节点图和未覆盖的工作流。

<a id="why-must-the-mcp-process-stay-running"></a>
### 为什么 MCP 进程必须保持运行？

该进程保留到 Blender 的串行化连接。每次调用都重新启动它会增加可避免的启动、传输和 agent-tool 开销。

<a id="does-it-require-docker"></a>
### 它需要 Docker 吗？

不需要。支持本地 stdio 的 MCP 客户端会直接启动 Node 服务器。Docker MCP Toolkit 是可选的打包和网关路线，而且尚未成为受支持的 ViperMesh 安装路径，因为 host-to-Blender loopback 连接仍需跨平台验证。

<a id="does-the-public-connector-require-vipermesh-cloud-authentication"></a>
### 公开连接器需要 ViperMesh 云身份验证吗？

不需要。公开插件和本地 MCP 服务器无需 ViperMesh 身份验证即可工作。未来托管模型和专有编排属于单独的产品能力。

<a id="can-it-use-installed-blender-addons"></a>
### 它可以使用已安装的 Blender 插件吗？

该连接器可以检查已安装插件，并支持受信任的本地自动化。未知插件操作在暴露为可调用代理能力前应先审查。

<a id="development"></a>
## 开发

```bash
npm install
npm run check
python -m py_compile addon/vipermesh-addon.py
```

在打开 pull request 前，请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)。

<a id="license-and-attribution"></a>
## 许可证和署名

ViperMesh for Blender 按 [MIT License](../../../LICENSE) 发布。它包含派生自 Siddharth Ahuja 的 [BlenderMCP](https://github.com/ahujasid/mcp-for-blender) 的工作。请参阅 [NOTICE.md](NOTICE.md) 了解署名和商标声明。
