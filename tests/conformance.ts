import assert from "node:assert/strict"
import fs from "node:fs"
import os from "node:os"
import path from "node:path"
import { Client } from "@modelcontextprotocol/sdk/client/index.js"
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js"
import { z } from "zod"

import type { McpCommand, McpResponse } from "../lib/mcp/types"
import { getBlenderAgentContext } from "../lib/portable-mcp/agent-context"
import {
  VIPERMESH_CONNECTOR_MANUAL,
  VIPERMESH_MCP_INSTRUCTIONS,
} from "../lib/portable-mcp/onboarding"
import { PORTABLE_MCP_TOOL_NAMES, createPortableBlenderMcpServer } from "../lib/portable-mcp/server"
import { createPortableMcpService } from "../lib/portable-mcp/service"
import { getGuidanceDocument, search3dGuidance } from "../lib/portable-mcp/guidance"

const addon = fs.readFileSync("addon/vipermesh-addon.py", "utf8")
assert.match(addon, /"name": "ViperMesh for Blender"/)
assert.match(addon, /ADDON_VERSION = \(1, 3, 0\)/)

assert.ok(PORTABLE_MCP_TOOL_NAMES.includes("bootstrap_vipermesh_session"))
assert.ok(PORTABLE_MCP_TOOL_NAMES.includes("call_blender_tool_batch"))
assert.ok(PORTABLE_MCP_TOOL_NAMES.includes("run_blender_scene_stage"))
assert.match(VIPERMESH_MCP_INSTRUCTIONS, /one persistent MCP server process/i)
assert.match(VIPERMESH_CONNECTOR_MANUAL, /execute_code/)
assert.match(getBlenderAgentContext().context, /Inspect/i)

const guide = getGuidanceDocument("spatial-validation.md")
assert.match(guide.title, /spatial/i)
const guidance = await search3dGuidance(
  { query: "grounding support placement", source: "local" },
  { semanticSearch: async () => [] }
)
assert.ok(guidance.results.length > 0)
assert.ok(guidance.results.every((result) => result.source === "tool-skills"))

let clientCreations = 0
const service = createPortableMcpService({
  checkConnection: async () => ({ connected: true }),
  createClient: () => {
    clientCreations += 1
    return {
      execute: async <T = unknown>(command: McpCommand): Promise<McpResponse<T>> => ({
        status: "success",
        result: { command: command.type } as T,
      }),
      close: async () => undefined,
    }
  },
  semanticSearch: async () => [],
})

const bootstrap = await service.bootstrapViperMeshSession()
assert.equal(bootstrap.connection.connected, true)
assert.equal(bootstrap.sessionModel, "persistent")
await service.callBlenderTool("get_scene_info")
await service.callBlenderTool("get_scene_info")
assert.equal(clientCreations, 1, "A session must reuse one Blender client")
await service.close()

const temp = fs.mkdtempSync(path.join(os.tmpdir(), "vipermesh-image-transport-"))
const pngPath = path.join(temp, "preview.png")
fs.writeFileSync(pngPath, Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=", "base64"))
const server = createPortableBlenderMcpServer(service)
const client = new Client({ name: "preview-conformance", version: "1.0.0" })
const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair()
const imageToolResult = z.object({
  content: z.array(z.object({ type: z.string(), mimeType: z.string().optional() })),
  structuredContent: z.record(z.string(), z.unknown()).optional(),
})
try {
  await Promise.all([server.connect(serverTransport), client.connect(clientTransport)])
  const result = imageToolResult.parse(await client.callTool({ name: "call_blender_tool", arguments: { name: "inspect_render_artifact", params: { image_path: pngPath } } }))
  assert.ok(result.content.some((item) => item.type === "image" && item.mimeType === "image/png"), "MCP clients must receive the actual preview image")
  const final = imageToolResult.parse(await client.callTool({ name: "run_blender_scene_stage", arguments: { stage: "finalize", targetNames: ["Subject"], renderPath: pngPath, preservePresentation: true } }))
  assert.ok(final.content.some((item) => item.type === "image"))
  assert.equal(final.structuredContent?.visualReviewRequired, true)
} finally {
  await client.close()
  await server.close()
  await service.close()
  fs.rmSync(temp, { recursive: true, force: true })
}

console.log("ViperMesh public connector conformance tests passed")
