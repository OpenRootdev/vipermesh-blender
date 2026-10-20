# Install ViperMesh Blender MCP

Canonical page: https://openrootdev.github.io/vipermesh-blender/setup/



← ViperMesh overview

Install ViperMeshfor Blender.

Connect an AI client to your local Blender scene using the MCP server and addon.




What you need

Blender 5.2 is the currently tested release target.

Node.js 20 or newer.

An AI client that supports local MCP servers over stdio. A client that accepts only remote server URLs cannot connect directly to this release.

The connector is free and MIT licensed. Your AI client or model may charge separately. Docker and a ViperMesh account are not required.




1. Enable the Blender addon

Download the versioned addon Python file or ZIP from the latest release. In Blender, open Edit → Preferences → Add-ons → Install from Disk, select the file and enable ViperMesh for Blender.

Open the 3D Viewport sidebar, select ViperMesh and click Start Local Bridge. Leave Blender and the bridge running. The default connection is 127.0.0.1:9876.




2. Install the local MCP server

Packaged installation

Download the v1.3.0 MCPB bundle and its SHA-256 checksum. Import it into a client that supports local MCPB extensions. The bundle includes the Node server and dependencies; Node.js and the separate Blender addon are still required.

Without an MCPB importer, extract the bundle as a ZIP into a permanent directory. Configure your client to launch node with the absolute path to server/index.mjs. Follow the bundle and checksum guide.

Build from source

git clone https://github.com/OpenRootdev/vipermesh-blender.git
cd vipermesh-blender
npm install
npm run build




3. Connect your AI client

For the source build, register the server once using the built entry point. Replace the example path with your own absolute path:

{
  "mcpServers": {
    "vipermesh-blender": {
      "command": "node",
      "args": ["C:/absolute/path/to/vipermesh-blender/dist/public-portable-blender-mcp.js"]
    }
  }
}

Configuration locations and top-level keys depend on the client. See the client setup guide and your client’s documentation. The client should keep one MCP process alive for the complete session.




4. Check the connection, then try a small edit

Ask your agent to call bootstrap_vipermesh_session first and inspect the connection result. Start with a small request, such as moving an object or checking whether it sits on its support. Inspect the resulting scene and images before trusting the edit.

Nine top-level MCP tools expose discovery, scene operations, checks and the Python fallback. This is not a hosted 3D generation model, and the public connector does not include private Studio asset libraries.




Common setup problems

My client cannot see the tools

Check the registered command and absolute file path. Confirm that your client supports local stdio MCP servers and can launch Node. Reload the client’s MCP connection according to its own instructions.

The tools appear, but Blender will not connect

Confirm Blender is open, the addon is enabled and Start Local Bridge is active. Keep server and addon bridge ports consistent. Keep the bridge on loopback; do not expose it publicly.

The assistant keeps restarting the server

Configure the client to manage one persistent subprocess. Running npm, npx or tsx separately for every tool call discards the existing session.

Is the connection sandboxed?

No. This is a trusted local connector. The Python fallback can execute code inside Blender. Use trusted clients and review destructive operations. Read the security boundary.


Report a setup problem · Documentation for agents · Harness Library listing

Client configuration: https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/client-setup.md
Bundle and checksums: https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/mcp-distribution.md
Security: https://github.com/OpenRootdev/vipermesh-blender/blob/main/SECURITY.md
