import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js"
import { z } from "zod"

import type { PortableMcpService } from "./service"
import { readPreviewImage } from "./preview"
import {
  VIPERMESH_CONNECTOR_MANUAL,
  VIPERMESH_CONNECTOR_MANUAL_URI,
  VIPERMESH_MCP_INSTRUCTIONS,
  VIPERMESH_OPERATING_CONTEXT_URI,
} from "./onboarding"

export const PORTABLE_MCP_TOOL_NAMES = [
  "bootstrap_vipermesh_session",
  "check_blender_connection",
  "list_blender_tools",
  "call_blender_tool",
  "call_blender_tool_batch",
  "run_blender_scene_stage",
  "get_blender_agent_context",
  "search_3d_guidance",
  "get_3d_guidance_document",
] as const

function structuredResult(result: Record<string, unknown>) {
  return {
    content: [
      {
        type: "text" as const,
        text: JSON.stringify(result, null, 2),
      },
    ],
    structuredContent: result,
  }
}

function toolError(error: unknown) {
  const message =
    error instanceof Error && error.message.trim()
      ? error.message.trim().slice(0, 1_000)
      : "Portable Blender MCP tool failed"

  return {
    content: [{ type: "text" as const, text: message }],
    isError: true,
  }
}

export function createPortableBlenderMcpServer(service: PortableMcpService) {
  const server = new McpServer({
    name: "vipermesh-blender",
    version: "1.3.0",
  }, {
    instructions: VIPERMESH_MCP_INSTRUCTIONS,
  })

  server.registerResource(
    "vipermesh-connector-manual",
    VIPERMESH_CONNECTOR_MANUAL_URI,
    {
      title: "ViperMesh for Blender Connector Manual",
      description: "Persistent-session setup, tool selection, workflow, and acceptance guidance.",
      mimeType: "text/markdown",
    },
    async () => ({
      contents: [{
        uri: VIPERMESH_CONNECTOR_MANUAL_URI,
        mimeType: "text/markdown",
        text: VIPERMESH_CONNECTOR_MANUAL,
      }],
    })
  )

  server.registerResource(
    "vipermesh-operating-context",
    VIPERMESH_OPERATING_CONTEXT_URI,
    {
      title: "ViperMesh Blender Operating Context",
      description: "Compact operating rules for an agent using the connector.",
      mimeType: "text/markdown",
    },
    async () => ({
      contents: [{
        uri: VIPERMESH_OPERATING_CONTEXT_URI,
        mimeType: "text/markdown",
        text: service.getBlenderAgentContext().context,
      }],
    })
  )

  server.registerTool(
    "bootstrap_vipermesh_session",
    {
      title: "Bootstrap ViperMesh Session",
      description:
        "Call once at session start. Checks Blender and returns compact operating context plus the recommended next calls for one persistent MCP session.",
      inputSchema: z.object({}),
    },
    async () => {
      try {
        return structuredResult(await service.bootstrapViperMeshSession())
      } catch (error) {
        return toolError(error)
      }
    }
  )

  server.registerTool(
    "check_blender_connection",
    {
      title: "Check Blender Connection",
      description:
        "Check whether the local ViperMesh Blender addon is responding on its configured loopback socket.",
      inputSchema: z.object({}),
    },
    async () => {
      try {
        return structuredResult(await service.checkBlenderConnection())
      } catch (error) {
        return toolError(error)
      }
    }
  )

  server.registerTool(
    "list_blender_tools",
    {
      title: "List Blender Tools",
      description:
        "Discover relevant Blender actions. Set includeSchemas=true with a focused query/category to retrieve JSON argument schemas; ordinary lists remain compact. execute_code stays available.",
      inputSchema: z.object({
        category: z.string().trim().min(1).max(64).optional(),
        query: z.string().trim().min(1).max(256).optional(),
        includeSchemas: z.boolean().optional(),
      }),
    },
    async (input) => {
      try {
        return structuredResult(service.listBlenderTools(input))
      } catch (error) {
        return toolError(error)
      }
    }
  )

  server.registerTool(
    "call_blender_tool",
    {
      title: "Call Blender Tool",
      description:
        "Call one approved ViperMesh Blender command with structured parameters.",
      inputSchema: z.object({
        name: z.string().trim().min(1).max(128),
        params: z.record(z.unknown()).default({}),
      }),
    },
    async ({ name, params }) => {
      try {
        const result = await service.callBlenderTool(name, params)
        const imagePath = name === "inspect_render_artifact" ? params.image_path
          : name === "render_image" || name === "render_thumbnail_to_path" ? params.output_path : undefined
        const preview = result.status === "success" && typeof imagePath === "string" ? await readPreviewImage(imagePath) : undefined
        const response = structuredResult({ ...result, ...(imagePath ? { visualReviewRequired: true, imageAttached: !!preview } : {}) })
        return { ...response, content: [...response.content, ...(preview ? [preview] : [])] }
      } catch (error) {
        return toolError(error)
      }
    }
  )

  server.registerTool(
    "call_blender_tool_batch",
    {
      title: "Call Blender Tool Batch",
      description:
        "Run an ordered bounded sequence of approved ViperMesh Blender commands through one persistent session. Use only when intermediate observations are not needed to choose the next command.",
      inputSchema: z.object({
        commands: z.array(z.object({
          name: z.string().trim().min(1).max(128),
          params: z.record(z.unknown()).default({}),
        })).min(1).max(32),
        stopOnError: z.boolean().optional(),
      }),
    },
    async (input) => {
      try {
        return structuredResult(await service.callBlenderToolBatch(input))
      } catch (error) {
        return toolError(error)
      }
    }
  )

  server.registerTool(
    "run_blender_scene_stage",
    {
      title: "Run Blender Scene Stage",
      description:
        "Run one compact scene-workflow stage over the persistent Blender session. Use build, inspect_preview, and finalize as separate decision points; standalone tools remain available for repairs and unusual work.",
      inputSchema: z.object({
        stage: z.enum(["build", "inspect_preview", "finalize"]),
        commands: z.array(z.object({
          name: z.string().trim().min(1).max(128),
          params: z.record(z.unknown()).default({}),
        })).min(1).max(32).optional(),
        targetNames: z.array(z.string().trim().min(1).max(256)).min(1).max(128).optional(),
        spatialRelations: z.array(z.record(z.unknown())).max(128).optional(),
        previewPath: z.string().trim().min(1).max(2_048).optional(),
        renderPath: z.string().trim().min(1).max(2_048).optional(),
        blendPath: z.string().trim().min(1).max(2_048).optional(),
        preservePresentation: z.boolean().optional(),
        preset: z.enum(["studio", "product", "indoor", "exterior", "night"]).optional(),
        cameraName: z.string().trim().min(1).max(256).optional(),
        resolutionX: z.number().int().min(64).max(8_192).optional(),
        resolutionY: z.number().int().min(64).max(8_192).optional(),
        samples: z.number().int().min(1).max(4_096).optional(),
        groundingTolerance: z.number().min(0).max(10).optional(),
      }),
    },
    async (input) => {
      try {
        const result = await service.runBlenderSceneStage(input)
        const imagePath = input.stage === "inspect_preview" ? input.previewPath : input.stage === "finalize" ? input.renderPath : undefined
        const inspected = result.results.some((item) => item.name === "inspect_render_artifact" && item.success === true)
        const preview = imagePath && inspected ? await readPreviewImage(imagePath) : undefined
        const response = structuredResult({ ...result, visualReviewRequired: !!imagePath, imageAttached: !!preview })
        return { ...response, content: [...response.content, ...(preview ? [preview] : [])] }
      } catch (error) {
        return toolError(error)
      }
    }
  )

  server.registerTool(
    "get_blender_agent_context",
    {
      title: "Get Blender Agent Context",
      description:
        "Load the public compact ViperMesh operating rules for persistent Blender MCP sessions.",
      inputSchema: z.object({}),
    },
    async () => {
      try {
        return structuredResult(service.getBlenderAgentContext())
      } catch (error) {
        return toolError(error)
      }
    }
  )

  server.registerTool(
    "search_3d_guidance",
    {
      title: "Search 3D Guidance",
      description:
        "Search checked-in ViperMesh 3D tool skills and optionally the configured semantic guidance store.",
      inputSchema: z.object({
        query: z.string().trim().min(1).max(2_000),
        limit: z.number().int().min(1).max(20).optional(),
        source: z.enum(["all", "local", "semantic"]).optional(),
        minSimilarity: z.number().min(0).max(1).optional(),
      }),
    },
    async (input) => {
      try {
        return structuredResult({ ...(await service.search3dGuidance(input)) })
      } catch (error) {
        return toolError(error)
      }
    }
  )

  server.registerTool(
    "get_3d_guidance_document",
    {
      title: "Get 3D Guidance Document",
      description:
        "Read one approved Markdown reference from the checked-in ViperMesh agent skill.",
      inputSchema: z.object({
        filename: z.string().trim().min(1).max(255),
      }),
    },
    async ({ filename }) => {
      try {
        return structuredResult(service.get3dGuidanceDocument(filename))
      } catch (error) {
        return toolError(error)
      }
    }
  )

  return server
}
