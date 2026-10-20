import { TOOL_REGISTRY } from "../orchestration/tool-registry"
import type { ToolMetadata } from "../blender/tool-metadata"
import { getBlenderToolInputSchema } from "../blender/tool-input-schema"

export const MAX_PORTABLE_COMMAND_PAYLOAD_BYTES = 256 * 1024
export const MAX_PORTABLE_BATCH_COMMANDS = 32

const portableTools = TOOL_REGISTRY

const portableToolNames = new Set(portableTools.map((tool) => tool.name))

export function listPortableBlenderTools(includeSchemas = false): ToolMetadata[] {
  return portableTools.map((tool) => ({ ...tool,
    ...(includeSchemas ? { inputSchema: getBlenderToolInputSchema(tool.name) } : {}),
  }))
}

export function isPortableBlenderToolAllowed(name: string): boolean {
  return portableToolNames.has(name)
}

export function validatePortableCommandPayload(
  params: Record<string, unknown>
): void {
  let serialized: string

  try {
    serialized = JSON.stringify(params)
  } catch {
    throw new Error("Blender tool parameters must be JSON serializable")
  }

  const size = Buffer.byteLength(serialized, "utf8")
  if (size > MAX_PORTABLE_COMMAND_PAYLOAD_BYTES) {
    throw new Error(
      `Blender tool parameter payload exceeds ${MAX_PORTABLE_COMMAND_PAYLOAD_BYTES} bytes`
    )
  }
}

export function validatePortableBatchLength(commandCount: number): void {
  if (!Number.isInteger(commandCount) || commandCount < 1) {
    throw new Error("A Blender tool batch must contain at least one command")
  }
  if (commandCount > MAX_PORTABLE_BATCH_COMMANDS) {
    throw new Error(
      `A Blender tool batch may contain at most ${MAX_PORTABLE_BATCH_COMMANDS} commands`
    )
  }
}
