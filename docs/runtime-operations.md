# Connector Runtime Reference

This English-only developer reference describes the unreleased usability
candidate. Use its source commit and addon fingerprint when testing; the existing
release version alone does not identify these changes. The ordinary GUI setup
and the nine-tool MCP gateway remain available. No Studio account is required.

## Background Blender

Run the shipped addon directly using Blender's Python entry point:

```bash
blender --background --factory-startup --disable-autoexec --python addon/vipermesh-addon.py -- --serve --port 9894 --idle-timeout 300
```

To edit a file, pass an approved source blend before the Python script. Never
overwrite the only source copy; save requested outputs to separate paths.

```bash
blender --background --disable-autoexec scene-copy.blend --python addon/vipermesh-addon.py -- --serve --port 9894 --max-runtime 1800
```

Configure the persistent Node MCP server with `BLENDER_MCP_HOST=127.0.0.1` and
`BLENDER_MCP_PORT=9894`. The headless Blender process and the stdio Node server
are different processes; keep both alive across actions. The client still uses
`bootstrap_vipermesh_session` and normal tools, not repeated shell invocations.

`VIPERMESH_BRIDGE_AUTOSTART=1` opts an enabled addon into starting its local
listener. `VIPERMESH_BRIDGE_PORT` sets that listener's port. Both are optional;
autostart is off by default. When this addon file is executed directly in
background mode, autostart also enters the service loop. Merely enabling an
installed addon with another background script does not keep Blender alive:
use the explicit `--serve` entry point or call `serve_headless` on the main thread.

`--idle-timeout` and `--max-runtime` are seconds; zero disables that limit. Limits
are checked between commands, not as unsafe interruption of an active render or
edit. Ctrl+C exits the service loop; an OS force-kill cannot guarantee cleanup.
The runner does not automatically save or install global preferences.

Network workers perform socket I/O and queue transfers only. All bpy operations
execute on Blender's main thread. GUI mode drains that queue with a persistent
timer; background mode uses its explicit loop without timer shims. UI-only
viewport commands return `UI_CONTEXT_REQUIRED` in background mode. Inspect data
or use a camera render there instead. File-load handling keeps the GUI queue
timer active and synchronizes the visible bridge status.

These are trusted local processes with code/file access, not authenticated
network services. Do not bind the bridge publicly to bypass WSL/container
networking. Native same-host setup remains the supported route.

## Action Schemas

Ordinary discovery remains compact. Request schemas only for relevant actions:

```json
{"name":"list_blender_tools","arguments":{"query":"set_object_transform","includeSchemas":true}}
```

Each returned action includes JSON Schema in `inputSchema`. The schemas are
generated from actual Python handler signatures, with reviewed basic types,
vector lengths and representative values. Case-normalized values and aliases
remain Blender-validated, rather than being rejected by overly narrow enums.
The Node gateway validates required keys,
unknown keys and declared types before dispatch; batches are fully prevalidated
before their first action. Optional arguments retain their Python defaults.

Nested, operation-dependent configurations that do not have a reviewed shape
are explicitly marked `x-blender-validation: runtime`. Their detailed semantics,
scene context and geometric correctness still require Blender checks. JSON
Schema is not proof that an edit is artistically correct. `execute_code` remains
available for unusual work; its code contents cannot be made safe by a string
schema.

After changing handler signatures, review the generator's constraints and run:

```bash
python scripts/maintenance/generate-blender-tool-schemas.py
npm run schemas:check
```

Commit generated schemas with the matching addon. CI refuses stale signatures.
The default discovery response does not include every schema, avoiding a large
unnecessary addition to the agent's context.

## Raw Addon TCP Contract

This is the custom addon protocol, **not** MCP JSON-RPC. MCP clients normally
use the Node gateway. Direct tests may use a trusted local TCP socket.

- Address: IPv4 loopback, default `127.0.0.1:9876`.
- Encoding: one UTF-8 JSON object per request; optional trailing whitespace/newline.
- Request: required string `type`, optional object `params` (default empty),
  optional string/integer `id`. Boolean IDs are not integers in this contract.
- One request in flight per connection. Wait for a complete response before
  sending the next. TCP packet boundaries are not message boundaries.
- Responses are complete, unframed JSON documents. Accumulate bytes until a full
  JSON value parses; do not assume one `recv` contains the response or a newline.
- Accepted requests echo their IDs. Connection/protocol errors may omit them.
  Legacy addon responses without IDs remain accepted by the Node client.
- Top-level `status: error` is failure. A handler may also return `result.error`
  with outer `status: success`; check both before accepting an operation.
- The addon refuses requests exceeding 10 MiB and bounds its command queue.
  The gateway separately limits serialized parameters to 256 KiB and batches
  to 32 actions. Bypassing Node bypasses those gateway policies.
- Split UTF-8 sequences are buffered. Coalesced pipelined JSON documents are
  refused with `PIPELINING_NOT_SUPPORTED` and the connection closes.
- Invalid UTF-8, invalid request shapes and obvious invalid JSON produce
  `INVALID_ENCODING`, `INVALID_REQUEST` or `INVALID_JSON`. Incomplete JSON can
  wait for more bytes; clients must impose request timeouts.
- Queue exhaustion produces `BRIDGE_BUSY`; optional providers depend on enabled
  scene flags. Viewport-only work requires GUI context.

```json
{"id":"check-1","type":"get_scene_info","params":{}}
```

```json
{"id":"check-1","status":"success","result":{"name":"Scene","object_count":3}}
```

The response example is abbreviated. A timeout/disconnect is **not cancellation**
of an edit already queued or running. Inspect the scene before deciding whether
to retry an uncertain mutation. The Node client closes an ambiguous connection,
rejects a premature close or mismatched response ID, and does not automatically
replay mutations. Reasoning pauses do not expire idle connections.

Direct-addon conformance (requires a local Blender executable):

```bash
python scripts/test/test_blender_bridge_protocol.py --blender /absolute/path/to/blender --addon addon/vipermesh-addon.py --output /new/disposable/test-output
```

The test starts and stops only its own process and saves only a fixture blend.
Never point disposable tests at a working user scene.

After `npm run build`, test the public SDK gateway through one retained session:

```bash
python scripts/test/test_blender_mcp_runtime.py --blender /absolute/path/to/blender --addon addon/vipermesh-addon.py --server dist/public-portable-blender-mcp.js --output /new/disposable/integration-output
```

Add `--gui` for the GUI-timer and viewport path. Both modes use a temporary
profile and factory scene, exercise batch prevalidation, edits, save/reopen and
a small Cycles camera render, then terminate only their own Blender process.
The tests require a Blender build with Cycles. Static RNA engine lists can omit
dynamically registered engines; render-setting validation uses Blender's actual
property assignment. `available_engines` is only a hint list and is labelled
`available_engines_complete: false`, not used to deny a registered engine.

## Curated Local Catalogs

From a source checkout with development dependencies installed:

```bash
npm run assets:catalog -- --root /absolute/path/to/ViperMeshAssets
```

The built package also provides `vipermesh-assets`:

```bash
vipermesh-assets --root /absolute/path/to/ViperMeshAssets
```

Optional `--out` chooses a manifest path; otherwise it writes `catalog/assets.json`.
Supported model files are `.blend`, `.glb`, `.gltf`, `.fbx` and `.obj`. This is a
filesystem indexer, not a downloader, quality judge or full material library.
It does not open Blender, authenticate to Studio or scan outside the chosen root.

New discovery skips `cache`, `incoming`, `previews`, `catalog`, hidden folders
and symlinks. Existing IDs, tags, categories, licenses, import settings and
unknown editorial fields survive refresh. Existing manually curated or offline
entries are retained; remove unwanted entries explicitly rather than relying
on a missing file to silently delete them. Duplicate IDs/paths and malformed
existing catalogs refuse refresh before replacing the manifest.

A same-directory lock refuses concurrent writers. The manifest is written to a
temporary file, flushed and atomically renamed. A leftover lock after a crash
requires verifying no refresh process is active before removing that lock;
do not delete a live writer's lock. Back up important catalogs independently.
New entries make no claim of having been validated in Blender.

Enable the addon local-library toggle and select this catalog/root. Named
collections or objects should be filled in for precise `.blend` imports.
Previews can sit next to model files. Poly Haven already has a provider import
path; persistent provider-to-catalog ingestion is a separate future feature.
