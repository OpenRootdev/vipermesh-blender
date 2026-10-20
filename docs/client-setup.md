# MCP Client Setup

## What Starts What

ViperMesh for Blender has two local connections:

1. An MCP client starts the ViperMesh Node server as a long-lived stdio
   subprocess.
2. The Node server opens and reuses a serialized TCP connection to the Blender
   addon on `127.0.0.1:9876`.

The MCP client is responsible for the server lifecycle. Register the server
once in the client, then use the MCP tools exposed in that client session.
Running a separate `npm`, `npx`, or `tsx` command for each tool call creates a
new server process and discards the persistent connection.

Docker is not required for clients that support local stdio MCP servers.

## Native Stdio Setup

Clone, install, and build the repository:

```bash
git clone https://github.com/OpenRootdev/vipermesh-blender.git
cd vipermesh-blender
npm install
npm run build
```

Use the built entry point from an absolute path. This avoids relying on a
client-specific working-directory option.

### Codex

```bash
codex mcp add vipermesh-blender -- node C:/absolute/path/to/vipermesh-blender/dist/public-portable-blender-mcp.js
```

Confirm the registration:

```bash
codex mcp list
```

Open a new Codex task if the current task does not reload MCP registrations.

### JSON-Configured Clients

Clients such as Claude Desktop and other hosts commonly accept a command and
argument array:

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

The configuration filename and top-level key vary by client. Use the client's
current MCP documentation, but keep the command itself equivalent.

## Client Compatibility

A client can use this release directly when it supports local MCP servers over
stdio and can launch a subprocess. MCP support alone does not guarantee that:

- some clients support local stdio and remote Streamable HTTP;
- some support only remote server URLs;
- some require a plugin, extension, or administrator policy before local
  process execution is allowed.

This release is stdio-only. A remote-only client needs a separately hosted MCP
transport or a compatible gateway; it cannot connect directly to the Blender
addon's TCP protocol.

## Docker MCP Toolkit

Docker MCP Toolkit can centralize containerized MCP servers and connect its
stdio gateway to supported clients. It is an optional distribution route, not
a requirement for ViperMesh.

ViperMesh does not currently publish a Docker MCP Catalog entry. The Blender
addon also remains loopback-only for local security. A container must reach
that host loopback service reliably, which varies with the Docker host,
networking mode, and client environment.

For that reason, native stdio is the supported setup today. Do not expose the
Blender bridge on a public interface merely to make a container connect. Docker
Toolkit instructions will be promoted to a supported path after an end-to-end
Windows, macOS, and Linux connectivity test defines a secure configuration.

Official references:

- [MCP transports](https://modelcontextprotocol.io/specification/latest/basic/transports)
- [Docker MCP Toolkit](https://docs.docker.com/ai/mcp-catalog-and-toolkit/)

## Verify The Session

1. Start Blender and the ViperMesh local bridge.
2. Open a new session in the configured MCP client.
3. Call `bootstrap_vipermesh_session`.
4. Confirm `connection.connected` is `true` and `sessionModel` is
   `persistent`.
5. Make two lightweight inspection calls. They should reuse one MCP process and
   one Blender client rather than starting new shell commands.
