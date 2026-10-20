export type ToolCategory =
  | "inspection"
  | "geometry"
  | "materials"
  | "lighting"
  | "camera"
  | "assets"
  | "advanced"
  | "other"

export interface ToolMetadata {
  name: string
  description: string
  category: ToolCategory
  parameters?: string
  inputSchema?: import("./tool-input-schema").BlenderInputSchema
}
