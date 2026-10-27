import type { McpCommand, McpResponse } from "../mcp/types"
import { getBlenderToolInputSchema as getInputSchema, validateBlenderToolArguments } from "../blender/tool-input-schema"

import {
  getGuidanceDocument,
  search3dGuidance,
  type GuidanceSearchInput,
} from "./guidance"
import {
  isPortableBlenderToolAllowed,
  listPortableBlenderTools,
  validatePortableBatchLength,
  validatePortableCommandPayload,
} from "./policy"
import {
  getBlenderAgentContext,
} from "./agent-context"

interface PortableMcpClient {
  execute<T = unknown>(command: McpCommand): Promise<McpResponse<T>>
  close(): Promise<void>
}

export interface PortableMcpServiceDependencies {
  checkConnection: () => Promise<{ connected: boolean; error?: string }>
  createClient: () => PortableMcpClient
  semanticSearch: (
    query: string,
    options: {
      limit: number
      source?: string
      minSimilarity: number
    }
  ) => Promise<Array<{
    id: string
    content: string
    metadata?: Record<string, unknown> | null
    source?: string
    similarity?: number
  }>>
  authorizeCapabilityInvocation?: (
    params: Record<string, unknown>
  ) => Promise<Record<string, unknown>>
}

export interface ListBlenderToolsInput {
  category?: string
  query?: string
  includeSchemas?: boolean
}

export interface BlenderToolBatchInput {
  commands: Array<{
    name: string
    params?: Record<string, unknown>
  }>
  stopOnError?: boolean
}

export type BlenderSceneWorkflowStage = "build" | "inspect_preview" | "finalize"

export interface BlenderSceneWorkflowInput {
  stage: BlenderSceneWorkflowStage
  commands?: BlenderToolBatchInput["commands"]
  targetNames?: string[]
  spatialRelations?: Array<Record<string, unknown>>
  previewPath?: string
  renderPath?: string
  blendPath?: string
  preservePresentation?: boolean
  preset?: "studio" | "product" | "indoor" | "exterior" | "night"
  cameraName?: string
  resolutionX?: number
  resolutionY?: number
  samples?: number
  groundingTolerance?: number
}

export function responseSucceeded(response: McpResponse) {
  if (response.status !== "success" && response.status !== "ok") return false
  return !(
    response.result &&
    typeof response.result === "object" &&
    !Array.isArray(response.result) &&
    "error" in response.result
  )
}

/** The client keeps `raw` (the whole socket payload) for internal diagnostics; agents never need a second copy. */
function leanResponse(response: McpResponse): McpResponse {
  const { raw: _raw, ...rest } = response
  return rest as McpResponse
}

const TOOL_WORDS = /[a-z0-9]+/g

/** Word-level tool ranking: every query word must hit a word of the tool; name hits outrank description hits. */
function rankTools<T extends { name: string; description: string; parameters?: string }>(tools: T[], query: string) {
  const terms = [...new Set(query.toLowerCase().match(TOOL_WORDS) ?? [])]
  if (!terms.length) return tools
  const scored = tools.map((tool) => {
    const nameWords: string[] = tool.name.toLowerCase().match(TOOL_WORDS) ?? []
    const textWords: string[] = `${tool.description} ${tool.parameters ?? ""}`.toLowerCase().match(TOOL_WORDS) ?? []
    let matched = 0
    let score = 0
    for (const term of terms) {
      const best = Math.max(
        nameWords.includes(term) ? 6 : nameWords.some((word) => word.startsWith(term)) ? 4 : 0,
        textWords.includes(term) ? 2 : textWords.some((word) => word.startsWith(term)) ? 1 : 0,
      )
      if (best) matched += 1
      score += best
    }
    return { tool, matched, score }
  }).filter((entry) => entry.matched > 0)
  // Prefer tools matching every word; fall back to the best partial matches rather than returning nothing.
  const topMatched = Math.max(0, ...scored.map((entry) => entry.matched))
  return scored
    .filter((entry) => entry.matched === topMatched)
    .sort((a, b) => b.score - a.score || a.tool.name.localeCompare(b.tool.name))
    .map((entry) => entry.tool)
}

function sanitizedError(error: unknown, fallback: string) {
  if (!(error instanceof Error)) return fallback
  const message = error.message.trim()
  return message ? message.slice(0, 1_000) : fallback
}

export function createPortableMcpService(
  dependencies: PortableMcpServiceDependencies
) {
  let sharedClient: PortableMcpClient | undefined
  let operationTail: Promise<void> = Promise.resolve()

  function client() {
    sharedClient ??= dependencies.createClient()
    return sharedClient
  }

  function serialized<T>(operation: () => Promise<T>): Promise<T> {
    const result = operationTail.then(operation, operation)
    operationTail = result.then(() => undefined, () => undefined)
    return result
  }

  function validateCommand(name: string, params: Record<string, unknown>) {
    if (!isPortableBlenderToolAllowed(name)) {
      throw new Error(`Blender tool is not available through the portable gateway: ${name}`)
    }
    validatePortableCommandPayload(params)
    validateBlenderToolArguments(name, params)
  }

  async function executeCommand(name: string, params: Record<string, unknown>) {
    validateCommand(name, params)
    if (
      name === "invoke_addon_capability" &&
      params.dry_run === false &&
      dependencies.authorizeCapabilityInvocation
    ) {
      params = await dependencies.authorizeCapabilityInvocation(params)
    }
    try {
      return leanResponse(await client().execute({ type: name, params }))
    } catch (error) {
      throw new Error(sanitizedError(error, `Blender tool call failed: ${name}`))
    }
  }

  async function executeBatch(input: BlenderToolBatchInput) {
    validatePortableBatchLength(input.commands.length)
    const commands = input.commands.map((command) => {
      const params = command.params ?? {}
      validateCommand(command.name, params)
      return { name: command.name, params }
    })
    const stopOnError = input.stopOnError ?? true
    const results: Array<{ name: string; response: McpResponse }> = []

    for (const command of commands) {
      const response = await executeCommand(command.name, command.params)
      results.push({ name: command.name, response })
      if (stopOnError && !responseSucceeded(response)) break
    }

    return {
      requested: commands.length,
      completed: results.length,
      stoppedEarly: results.length < commands.length,
      stopOnError,
      results,
    }
  }

  return {
    async bootstrapViperMeshSession() {
      const connection = await this.checkBlenderConnection()
      const context = getBlenderAgentContext()
      return {
        connection,
        sessionModel: "persistent" as const,
        context,
        nextCalls: connection.connected
          ? [
              "call_blender_tool(name=get_scene_info)",
              "search_3d_guidance(query=<task-specific query>)",
              "list_blender_tools(query=<needed capability>)",
            ]
          : [
              "Start the ViperMesh local bridge in Blender",
              "check_blender_connection",
            ],
        warning:
          "Keep this MCP server process alive. Do not launch a new npm, npx, or tsx process for each Blender operation.",
      }
    },

    async checkBlenderConnection() {
      try {
        return await dependencies.checkConnection()
      } catch (error) {
        return {
          connected: false,
          error: sanitizedError(error, "Blender connection check failed"),
        }
      }
    },

    listBlenderTools(input: ListBlenderToolsInput = {}) {
      const category = input.category?.trim().toLowerCase()
      const query = input.query?.trim().toLowerCase()
      const inCategory = listPortableBlenderTools().filter((tool) =>
        !category || tool.category.toLowerCase() === category)
      const tools = (query ? rankTools(inCategory, query) : inCategory).map(tool => input.includeSchemas
        ? { ...tool, inputSchema: getInputSchema(tool.name) } : tool)

      return {
        count: tools.length,
        tools,
        excludedTools: [],
      }
    },

    async callBlenderTool(
      name: string,
      params: Record<string, unknown> = {}
    ): Promise<McpResponse> {
      validateCommand(name, params)
      return serialized(() => executeCommand(name, params))
    },

    async callBlenderToolBatch(input: BlenderToolBatchInput) {
      return serialized(() => executeBatch(input))
    },

    async runBlenderSceneStage(input: BlenderSceneWorkflowInput) {
      return serialized(async () => {
        let commands: BlenderToolBatchInput["commands"]

        if (input.stage === "build") {
          if (!input.commands?.length) throw new Error("The build stage requires commands")
          commands = input.commands
        } else if (input.stage === "inspect_preview") {
          if (!input.targetNames?.length) throw new Error("The inspect_preview stage requires targetNames")
          if (!input.previewPath) throw new Error("The inspect_preview stage requires previewPath")
          commands = [
            {
              name: "inspect_scene_grounding",
              params: {
                tolerance: input.groundingTolerance ?? 0.035,
                include_supports: true,
                max_objects: 128,
              },
            },
            ...(input.spatialRelations?.length ? [{
              name: "inspect_spatial_relations",
              params: { relations: input.spatialRelations },
            }] : []),
            {
              name: "render_thumbnail_to_path",
              params: {
                output_path: input.previewPath,
                target_names: input.targetNames,
                preset: input.preset ?? "studio",
                camera_name: input.cameraName ?? "ViperMesh_Workflow_Camera",
                resolution: input.resolutionX ?? 768,
                samples: input.samples ?? 16,
                frame_camera: true,
              },
            },
            {
              name: "inspect_render_artifact",
              params: { image_path: input.previewPath },
            },
          ]
        } else {
          if (!input.targetNames?.length) throw new Error("The finalize stage requires targetNames")
          if (!input.renderPath) throw new Error("The finalize stage requires renderPath")
          const cameraName = input.cameraName ?? "ViperMesh_Workflow_Camera"
          commands = [
            ...(!input.preservePresentation ? [
            {
              name: "setup_studio_scene",
              params: {
                target_names: input.targetNames,
                preset: input.preset ?? "studio",
                camera_name: cameraName,
                resolution_x: input.resolutionX ?? 900,
                resolution_y: input.resolutionY ?? 700,
                samples: input.samples ?? 32,
              },
            },
            {
              name: "frame_camera_to_targets",
              params: {
                target_names: input.targetNames,
                camera_name: cameraName,
                desired_frame_fill: 0.68,
                frame_margin: 0.08,
                set_active: true,
                set_dof_focus: false,
              },
            },
            ] : []),
            {
              name: "validate_studio_scene",
              params: { target_names: input.targetNames, require_lights: !input.preservePresentation, ...(input.cameraName || !input.preservePresentation ? { camera_name: cameraName } : {}) },
            },
            ...(input.spatialRelations?.length ? [{
              name: "inspect_spatial_relations",
              params: { relations: input.spatialRelations },
            }] : []),
          ]
        }

        const batch = await executeBatch({ commands, stopOnError: true })
        let results = batch.results

        if (input.stage === "finalize" && workflowReady(results)) {
          const finalBatch = await executeBatch({
            commands: [
              { name: "render_image", params: { output_path: input.renderPath!, file_format: "PNG" } },
              { name: "inspect_render_artifact", params: { image_path: input.renderPath! } },
              ...(input.blendPath ? [{ name: "save_blend_file", params: { filepath: input.blendPath, make_dirs: true, check_existing: true } }] : []),
            ],
            stopOnError: true,
          })
          results = [...results, ...finalBatch.results]
        }

        const ready = workflowReady(results)
        const expectedCount = input.stage === "finalize" ? commands.length + 2 + (input.blendPath ? 1 : 0) : commands.length
        return {
          stage: input.stage,
          requested: expectedCount,
          completed: results.length,
          stoppedEarly: results.length < expectedCount,
          ready,
          results: results.map(({ name, response }) => compactResponse(name, response)),
          nextDecision: input.stage === "build"
            ? "Run inspect_preview and review its artifact before finalizing."
            : input.stage === "inspect_preview"
              ? ready
                ? "Review the preview visually, then run finalize or repair and repeat inspect_preview."
                : "Repair reported structural or artifact issues, then repeat inspect_preview."
              : ready
                ? "Review the final render visually before accepting the scene."
                : results.length < expectedCount
                  ? "Final output was withheld because studio validation did not pass."
                  : "Final artifacts were produced, but artifact inspection needs review before acceptance.",
        }
      })
    },

    getBlenderAgentContext() {
      return getBlenderAgentContext()
    },

    async search3dGuidance(input: GuidanceSearchInput) {
      return search3dGuidance(input, {
        semanticSearch: dependencies.semanticSearch,
      })
    },

    get3dGuidanceDocument(filename: string) {
      return getGuidanceDocument(filename)
    },

    async close() {
      await operationTail
      const currentClient = sharedClient
      sharedClient = undefined
      await currentClient?.close().catch(() => undefined)
    },
  }
}

function compactResponse(name: string, response: McpResponse) {
  const result = response.result && typeof response.result === "object" && !Array.isArray(response.result)
    ? response.result as Record<string, unknown>
    : undefined
  const summary: Record<string, unknown> = {
    name,
    status: response.status,
    success: responseSucceeded(response),
  }

  if (response.message) summary.message = response.message
  if (!result) return summary

  const keys = [
    "ready", "success", "message", "error", "output_path", "filepath",
    "checked_count", "pass_count", "fail_count", "floating_count",
    "high_priority_floating_count", "low_priority_floating_count",
    "below_ground_count", "part_count", "object_count", "deleted_count",
    "softened_count", "missing_targets", "warnings", "errors", "camera",
  ]
  for (const key of keys) {
    if (key in result) summary[key] = result[key]
  }
  if (Array.isArray(result.relations)) {
    summary.failed_relations = result.relations.filter((relation) => relation && typeof relation === "object" && relation.passed === false).slice(0, 16)
  }
  for (const key of ["high_priority_floating_objects", "below_ground_objects"]) {
    if (Array.isArray(result[key])) summary[key] = result[key].slice(0, 16)
  }
  return summary
}

function workflowReady(results: Array<{ name: string; response: McpResponse }>) {
  return results.every(({ response }) => {
    if (!responseSucceeded(response)) return false
    const result = response.result
    if (!result || typeof result !== "object" || Array.isArray(result)) return true
    if ("ready" in result && result.ready === false) return false
    if ("high_priority_floating_count" in result && Number(result.high_priority_floating_count) > 0) return false
    if ("below_ground_count" in result && Number(result.below_ground_count) > 0) return false
    if ("fail_count" in result && Number(result.fail_count) > 0) return false
    if ("camera" in result && result.camera && typeof result.camera === "object" && "active" in result.camera && result.camera.active === false) return false
    return true
  })
}

export type PortableMcpService = ReturnType<typeof createPortableMcpService>
