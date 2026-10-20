<a id="changelog"></a>
# 更新日志

ViperMesh for Blender 的所有重要变更都记录在这里。

<a id="unreleased"></a>
## [未发布]

<a id="130---2026-10-07"></a>
## [1.3.0] - 2026-10-07

<a id="added"></a>
### 新增

- 连接到仓库的 GitHub Pages 概览、设置说明和诚实的能力边界。
- 面向支持图像感知的 MCP 客户端的内联有界 PNG/JPEG 输出。
- 当前 Blender 工具表面中已存在的几何/变形诊断和受保护的插件操作，已同步到公开分发版本。

<a id="changed"></a>
### 变更

- finalize 可以保留现有相机/灯光并在不保存 blend 文件的情况下渲染。具名空间失败会阻止最终输出并保留修复细节。
- 移除固定预览数量；要求基于任务的视觉审查，并披露未解决缺陷，而不是把文件健康状态当作质量结论。
- Blend 保存现在是显式操作，并会在分阶段 finalize 中拒绝已有目标。
- 更新了公开依赖锁和 SDK 最低版本；干净安装审计结果明确。
- 包验证会检查每个随包发布的技能参考。
- 修正了备份或导出失败后的 retarget 回滚、部分导入清理、已取消 operator 处理、enum-flag 参数转换和实现感知的插件指纹。添加了 Blender 运行时回归测试。

<a id="changed-1"></a>
### 变更

- 用简洁、可安装的公开代理技能和可调整的参考文档替换了导出的私有 tool-guide 语料库。
- 添加了明确的原生 stdio 客户端设置，并澄清 Docker MCP Toolkit 路线是可选的、尚未受支持。
- 添加导出检查，防止私有 `data/tool-guides` 内容进入公开发布。

<a id="120---2026-07-25"></a>
## [1.2.0] - 2026-07-25

<a id="added-1"></a>
### 新增

- 持久 stdio MCP 服务器，每个代理会话对应一个串行化 Blender 连接。
- Blender 插件，具有明确的 Stopped、Ready、Agent connected 和 Error 状态。
- 确定性的场景检查、组装、材质、灯光、相机、渲染、动画、绑定、UV、导出和重拓扑工具。
- 有界批量调用，以及分阶段构建、预览检查和 finalize 工作流。
- 会话 bootstrap、MCP resources、紧凑操作上下文，以及为新代理签入的任务指导。
- 为真正自定义的 Blender 工作提供明确的 `execute_code` 回退。
- 仅限本地的 loopback 传输和公开发布验证。

[未发布]: https://github.com/OpenRootdev/vipermesh-blender/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/OpenRootdev/vipermesh-blender/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/OpenRootdev/vipermesh-blender/releases/tag/v1.2.0
