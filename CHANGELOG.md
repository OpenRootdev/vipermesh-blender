# Changelog

All notable changes to ViperMesh for Blender are documented here.

## [Unreleased]

### Fixed

- Viewport captures (`get_viewport_screenshot`, `render_viewport_to_path`) use a
  viewport render instead of a screen grab: no splash screen or popups in the
  image, and EEVEE shaders finish compiling first. Results name the
  `capture_method`; a screen-grab fallback is reported in `warnings`.
- Studio thumbnails and `setup_studio_scene` pull the camera back until every
  target fits the frame (a row of objects was cropped at the edges). The result
  reports `camera.framing`.

## [1.3.0] - 2026-10-07

### Added

- Repository-connected GitHub Pages overview, setup and honest capability limits.
- Inline bounded PNG/JPEG output for image-aware MCP clients.
- Geometry/deformation diagnostics and guarded addon operations already present
  in the current Blender tool surface, synchronized into the public distribution.

### Changed

- Finalize can preserve existing camera/lighting and render without saving a blend
  file. Named spatial failures block final output and retain repair details.
- Removed fixed preview counts; require task-based visual review and disclose
  unresolved defects instead of treating file health as a quality verdict.
- Blend saves are explicit and refuse existing destinations in staged finalize.
- Updated the public dependency lock and SDK floor; clean install audit is clear.
- Package validation checks every shipped skill reference.
- Corrected retarget rollback after backup or export failure, partial-import
  cleanup, cancelled operator handling, enum-flag argument conversion and
  implementation-aware addon fingerprints. Added Blender runtime regressions.

### Changed

- Replaced the exported private tool-guide corpus with a concise, installable
  public agent skill and adaptable reference documents.
- Added explicit native stdio client setup and clarified the optional,
  not-yet-supported Docker MCP Toolkit route.
- Added export checks that prevent private `data/tool-guides` content from
  entering public releases.

## [1.2.0] - 2026-07-25

### Added

- Persistent stdio MCP server with one serialized Blender connection per agent
  session.
- Blender addon with explicit Stopped, Ready, Agent connected, and Error
  states.
- Deterministic scene inspection, assembly, materials, lighting, camera,
  rendering, animation, rigging, UV, export, and retopology tools.
- Bounded batch calls and staged build, preview-inspection, and finalize
  workflows.
- Session bootstrap, MCP resources, compact operating context, and checked-in
  task guidance for fresh agents.
- Explicit `execute_code` fallback for genuinely custom Blender work.
- Local-only loopback transport and public release validation.

[Unreleased]: https://github.com/OpenRootdev/vipermesh-blender/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/OpenRootdev/vipermesh-blender/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/OpenRootdev/vipermesh-blender/releases/tag/v1.2.0
