# MCP Distribution

ViperMesh for Blender is published as a local stdio connector. It does not
host Blender, supply an AI model, or include the private ViperMesh Studio and
its complete benchmarked harness.

## Published Listings

- [Smithery: ker102/vipermesh-blender](https://smithery.ai/servers/ker102/vipermesh-blender)
- [Official MCP Registry: io.github.Ker102/vipermesh-blender](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.Ker102/vipermesh-blender)
- [GitHub release v1.3.0](https://github.com/OpenRootdev/vipermesh-blender/releases/tag/v1.3.0)

The official registry hosts metadata. The MCPB package is hosted in the
GitHub release. Smithery's listing also contains the same bundle and the nine
MCP tool schemas discovered from the packaged server.

## Bundle Setup

1. Install and enable the Blender addon using the [main installation guide](../README.md#install).
2. Download [vipermesh-blender-1.3.0.mcpb](https://github.com/OpenRootdev/vipermesh-blender/releases/download/v1.3.0/vipermesh-blender-1.3.0.mcpb)
   and its [SHA-256 file](https://github.com/OpenRootdev/vipermesh-blender/releases/download/v1.3.0/vipermesh-blender-1.3.0.mcpb.sha256).
3. Import the bundle into an MCPB-compatible client, following that client's
   local-extension instructions. Node.js is required by the bundle's launch
   configuration. Keep the bridge port at `9876` unless your addon uses a
   different port.
4. Start the local Blender bridge, then call `bootstrap_vipermesh_session`
   from the AI client and inspect the connection result.

Clients without MCPB imports can use the [source installation](client-setup.md).
Alternatively, the MCPB is a ZIP archive: extract it into a permanent directory
and register `node` with the absolute path to `server/index.mjs` as its argument.
The extracted package contains its runtime dependencies and local guidance;
no `npm install` is needed. Start it once as a persistent stdio subprocess,
not once per Blender operation.

The bridge stays on `127.0.0.1`. Remote-only clients cannot directly use this
local connector. Do not expose Blender's bridge publicly to make them connect.

## Release Integrity And Validation

Version `1.3.0` is built from source commit
`781700be4f0fb32b135d3f5cb7da012ce8fc4abd`.

Bundle SHA-256:

```text
45f8cee90540e9f906b8e817efb6fa0a1302f8dba515522dc3682d328a90206c
```

Source TypeScript and conformance checks, addon Python syntax, package-schema
validation, MCP initialization, nine-tool discovery, and local guidance
lookups passed. The release download was checked against this checksum before
registry publication.

These package checks do not establish live Blender compatibility for every
client. A live scene test and end-to-end MCPB installation test remain pending
for this bundle. Test on a disposable scene, review destructive operations,
and follow the [security guidance](../SECURITY.md).

## Maintainer Notes

The published registry metadata is tracked in [server.json](../server.json).
For a new release, rebuild and validate the bundle, upload its exact bytes and
checksum to the release, then update the version, source commit, download URL,
and hash together before publishing metadata.

The MCPB manifest lists tool names. Smithery publication additionally needs
the complete `tools/list` schemas from the packaged server; names alone do not
satisfy its server-card validation. Keep those schemas consistent with the
release instead of inventing or dropping tool definitions.
