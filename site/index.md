# ViperMesh: Blender MCP server and addon

> Free, open-source local AI assistance for Blender scene editing, inspection and reusable 3D operations.

Canonical page: https://openrootdev.github.io/vipermesh-blender/
Repository: https://github.com/OpenRootdev/vipermesh-blender
License: MIT, with upstream attribution in NOTICE.md.

ViperMesh uses two local parts. A compatible AI client launches one persistent Node MCP process over stdio. That process connects to the Blender addon through a serialized loopback TCP bridge, by default 127.0.0.1:9876.

Ready-made actions cover scene arrangement, materials, lighting, cameras, geometry and UV preparation, rigging, weights, animation operations, export and diagnostics. Nine top-level MCP tools expose these capabilities. Agents should call bootstrap_vipermesh_session first. Python execution remains available for custom work.

Scene checks and visual inspection help an agent repair its work. Fewer generated tokens, faster work and better results are goals, not universal guarantees. Results depend on the model, scene and task.

The connector is not a hosted generation model. It does not bundle an AI model, cloud routing, private Studio asset libraries, authentication or billing. Docker and a ViperMesh account are not required; model access may cost separately. It is a trusted local connector, not a sandbox.

## Install

Blender 5.2 is the currently tested release target. Node.js 20+ and a client capable of local stdio MCP are required. Enable the separate Blender addon and start the local bridge. Import the MCPB bundle in a supported client, or build the source and register the built entry point. Keep one process running for the session.

- [Installation and troubleshooting](https://openrootdev.github.io/vipermesh-blender/setup/index.md)
- [Client configuration](https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/client-setup.md)
- [Release bundles](https://github.com/OpenRootdev/vipermesh-blender/releases)
- [Connector manual](https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/portable-blender-mcp.md)
- [Agent skill](https://github.com/OpenRootdev/vipermesh-blender/blob/main/skills/using-vipermesh-blender/SKILL.md)
- [Security boundary](https://github.com/OpenRootdev/vipermesh-blender/blob/main/SECURITY.md)
- [Illustrated overview](https://openrootdev.github.io/vipermesh-blender/#overview)
- [Harness Library](https://openrootdev.github.io/harness-library/harnesses/vipermesh-blender/)
