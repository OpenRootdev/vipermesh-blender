<a id="public-connector-release-checklist"></a>
# 公开连接器发布清单

公开仓库由
`config/public-blender-connector-files.json` 生成。切勿 fork 或复制私有仓库历史。

<a id="current-release"></a>
## 当前发布

- Repository: https://github.com/OpenRootdev/vipermesh-blender
- Release target: https://github.com/OpenRootdev/vipermesh-blender/releases/tag/v1.3.0
- Source release target: `v1.3.0`
- Blender compatibility target: 5.2
- CI: standalone typecheck、一致性测试、构建、包验证、npm audit 和插件 Python 编译
- Historical live validation (v1.2.0): persistent stdio MCP discovery、scene calls、mutation、staged preview/finalize、save、local guidance 和 `execute_code` fallback
- Current launch checks: isolated package conformance、inline image transport、render-only/preserved-presentation stages、spatial failure withholding、dependency audit、Python compilation 和 desktop/mobile site review。完整实时代理性能会在下一次 demo pilot 中评估。

<a id="before-export"></a>
## 导出前

- 运行 `npm run validate:public-blender-connector`。
- 运行便携 MCP 网关和插件 UI focused tests。
- 使用 `python -m py_compile` 编译插件。
- 在当前 Blender 5.2 release 中安装生成的插件。
- 验证 Stopped、Ready、Agent connected 和 Error UI 状态。
- 通过新的 MCP 客户端验证 bootstrap、scene inspection、one mutation、preview inspection、final render、save 和 shutdown。

<a id="export-safety"></a>
## 导出安全

- 只导出 manifest 条目。
- 拒绝重复目标、缺失文件、绝对路径、traversal、私有应用路径、secrets、credentials、internal benchmark evidence 和 competitor-specific provider code。
- 创建 GitHub 仓库前，再次扫描生成目录。
- 将 `Ker102/vipermesh-blender` 创建为没有继承私有提交的新仓库。

<a id="release"></a>
## 发布

1. 在生成目录中安装依赖并运行 `npm run check`。
2. 将插件打包为 release artifact。
3. 标记连接器版本。
4. 只在检查包内容后发布 MCP 包。
5. 将私有 ViperMesh 产品固定到已发布的连接器版本。
6. 独立验证公开安装路径。
7. 只有到这一步，才更改 ViperMesh 产品仓库可见性。
