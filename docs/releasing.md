# Public Connector Release Checklist

The public repository is generated from
`config/public-blender-connector-files.json`. Never fork or copy the private
repository history.

## Current Release

- Repository: https://github.com/OpenRootdev/vipermesh-blender
- Release target: https://github.com/OpenRootdev/vipermesh-blender/releases/tag/v1.3.0
- Source release target: `v1.3.0`
- Blender compatibility target: 5.2
- CI: standalone typecheck, conformance tests, build, package validation, npm
  audit, and addon Python compilation
- Historical live validation (v1.2.0): persistent stdio MCP discovery, scene calls, mutation,
  staged preview/finalize, save, local guidance, and `execute_code` fallback
- Current launch checks: isolated package conformance, inline image transport,
  render-only/preserved-presentation stages, spatial failure withholding,
  dependency audit, Python compilation, and desktop/mobile site review. Full
  live agent performance is evaluated in the next demo pilot.

## Before Export

- Run `npm run validate:public-blender-connector`.
- Run the portable MCP gateway and addon UI focused tests.
- Compile the addon with `python -m py_compile`.
- Install the generated addon in the current Blender 5.2 release.
- Verify Stopped, Ready, Agent connected, and Error UI states.
- Verify bootstrap, scene inspection, one mutation, preview inspection, final
  render, save, and shutdown through a fresh MCP client.

## Export Safety

- Export only manifest entries.
- Reject duplicate targets, missing files, absolute paths, traversal, private
  application paths, secrets, credentials, internal benchmark evidence, and
  competitor-specific provider code.
- Scan the generated directory again before creating the GitHub repository.
- Create `Ker102/vipermesh-blender` as a new repository with no inherited
  private commits.

## Release

1. Install dependencies and run `npm run check` in the generated directory.
2. Package the addon as a release artifact.
3. Tag the connector version.
4. Publish the MCP package only after its package contents are inspected.
5. Pin the private ViperMesh product to the released connector version.
6. Verify the public install path independently.
7. Only then change the ViperMesh product repository visibility.
