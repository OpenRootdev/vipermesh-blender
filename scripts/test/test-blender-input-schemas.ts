import assert from "node:assert/strict"
import { TOOL_REGISTRY } from "../../lib/orchestration/tool-registry"
import { getBlenderToolInputSchema, validateBlenderToolArguments } from "../../lib/blender/tool-input-schema"
import { createPortableMcpService } from "../../lib/portable-mcp/service"

async function main() {
for (const tool of TOOL_REGISTRY) {
  const schema = getBlenderToolInputSchema(tool.name)
  assert.equal(schema.type, "object", tool.name)
  assert.ok(schema.properties, tool.name)
}
assert.doesNotThrow(() => validateBlenderToolArguments("set_object_transform", { name: "Cube", location: [1, 2, 3] }))
assert.doesNotThrow(() => validateBlenderToolArguments("set_object_transform", { name: "Cube", location: null }))
assert.doesNotThrow(() => validateBlenderToolArguments("import_local_asset", { asset_id: "chair", scale: 0.5 }))
assert.doesNotThrow(() => validateBlenderToolArguments("execute_code", { code: "print('custom work')" }))
for (const params of [{}, { name: 3 }, { name: "Cube", location: [1, 2] }, { name: "Cube", typo: true }]) {
  assert.throws(() => validateBlenderToolArguments("set_object_transform", params), /Invalid arguments/)
}
assert.doesNotThrow(() => validateBlenderToolArguments("align_object_to_surface", { name: "Cube", placement: "on-top-of", axis: "z" }))
assert.doesNotThrow(() => validateBlenderToolArguments("add_light", { light_type: "area" }))
assert.throws(() => validateBlenderToolArguments("align_object_to_surface", { name: "Cube", axis: 3 }), /Invalid arguments/)
let dispatched = 0
const service = createPortableMcpService({
  checkConnection: async () => ({ connected: true }), semanticSearch: async () => [],
  createClient: () => ({ execute: async () => { dispatched++; return { status: "success" } }, close: async () => undefined }),
})
assert.ok(!("inputSchema" in service.listBlenderTools({ query: "set_object_transform" }).tools[0]))
assert.equal(service.listBlenderTools({ query: "set_object_transform", includeSchemas: true }).tools[0].inputSchema?.type, "object")
await assert.rejects(service.callBlenderToolBatch({ commands: [
  { name: "get_scene_info" }, { name: "set_object_transform", params: { location: [1, 2] } },
] }), /Invalid arguments/)
assert.equal(dispatched, 0, "Validate the whole batch before the first mutation")
await service.close()
console.log("Blender input-schema checks passed")
}
main().catch(error => { console.error(error); process.exitCode = 1 })
