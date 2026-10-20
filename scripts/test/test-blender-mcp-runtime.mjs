import assert from 'node:assert/strict';
import { appendFileSync, existsSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport, getDefaultEnvironment } from '@modelcontextprotocol/sdk/client/stdio.js';

const [server, port, output, mode] = process.argv.slice(2);
const transport = new StdioClientTransport({ command: process.execPath, args: [server],
  env: { ...getDefaultEnvironment(), BLENDER_MCP_HOST: '127.0.0.1', BLENDER_MCP_PORT: port }, stderr: 'pipe' });
transport.stderr?.on('data', chunk => appendFileSync(path.join(output, 'mcp.stderr.log'), chunk));
const client = new Client({ name: 'vipermesh-runtime-integration', version: '0.1.0' });
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args }, undefined, { timeout: 60000 });
  const body = result.structuredContent ?? JSON.parse(result.content.find(item => item.type === 'text').text);
  appendFileSync(path.join(output, 'calls.jsonl'), `${JSON.stringify({ name, args, isError: result.isError ?? false, body })}\n`);
  assert.ok(!result.isError, JSON.stringify(result));
  return body;
}
async function action(name, params = {}) {
  const result = await call('call_blender_tool', { name, params });
  assert.equal(result.status, 'success', JSON.stringify(result));
  assert.ok(!result.result?.error, JSON.stringify(result));
  return result.result;
}
try {
  await client.connect(transport);
  assert.equal((await client.listTools()).tools.length, 9);
  assert.equal((await call('bootstrap_vipermesh_session')).connection.connected, true);
  const listed = await call('list_blender_tools', { query: 'set_object_transform', includeSchemas: true });
  assert.equal(listed.tools.find(tool => tool.name === 'set_object_transform').inputSchema.type, 'object');
  const invalid = await client.callTool({ name: 'call_blender_tool_batch', arguments: { commands: [
    { name: 'add_mesh_primitive', params: { primitive_type: 'cube', name: 'MustNotExist' } },
    { name: 'set_object_transform', params: { location: [1, 2] } },
  ] } });
  assert.equal(invalid.isError, true, 'Reject the whole invalid batch before dispatch');
  await action('execute_code', { code: "import bpy,threading\nassert threading.current_thread() is threading.main_thread()\nassert 'MustNotExist' not in bpy.data.objects\nprint('MAIN_THREAD_AND_PREVALIDATION_VERIFIED')" });
  await action('add_mesh_primitive', { primitive_type: 'cube', name: 'McpRuntimeProbe', size: 0.8 });
  await action('set_object_transform', { name: 'McpRuntimeProbe', location: [0, 0, 0.5] });
  await action('get_object_info', { name: 'McpRuntimeProbe' });
  const blend = path.join(output, 'mcp-runtime.blend');
  await action('save_blend_file', { filepath: blend });
  assert.ok(existsSync(blend));
  await action('execute_code', { code: `import bpy\nbpy.ops.wm.open_mainfile(filepath=${JSON.stringify(blend)})` });
  await action('get_object_info', { name: 'McpRuntimeProbe' });
  if (mode === 'gui') {
    const screenshot = path.join(output, 'viewport.png');
    await action('get_viewport_screenshot', { filepath: screenshot, max_size: 640 });
    assert.ok(existsSync(screenshot));
  } else {
    const refusal = await call('call_blender_tool', { name: 'get_viewport_screenshot', params: {} });
    assert.equal(refusal.code, 'UI_CONTEXT_REQUIRED');
  }
  await action('set_render_settings', { engine: 'CYCLES', resolution_x: 128, resolution_y: 128,
    resolution_percentage: 100, samples: 2, use_denoising: false });
  const unsupported = await call('call_blender_tool', { name: 'set_render_settings', params: { engine: 'NOT_A_REAL_ENGINE' } });
  assert.match(unsupported.result.error, /not available/);
  await action('execute_code', { code: "import bpy\nassert bpy.context.scene.render.engine == 'CYCLES'\nprint('DYNAMIC_ENGINE_AND_INVALID_ENGINE_VERIFIED')" });
  await action('render_image', { output_path: path.join(output, 'camera.png'), file_format: 'PNG' });
  assert.ok(existsSync(path.join(output, 'camera.png')));
  await action('get_scene_info');
  writeFileSync(path.join(output, 'result.json'), JSON.stringify({ passed: true, mode,
    checks: ['persistent-sdk-session', 'schemas', 'batch-prevalidation', 'main-thread', 'mutate-inspect',
      'save-reopen', mode === 'gui' ? 'gui-viewport' : 'viewport-refusal', 'camera-render'] }, null, 2));
} finally { await client.close(); }
