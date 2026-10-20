import { z } from "zod"
import generated from "./tool-input-schemas.json"

export interface BlenderInputSchema {
  type?: string
  properties?: Record<string, BlenderInputSchema>
  required?: string[]
  additionalProperties?: boolean
  items?: BlenderInputSchema
  minItems?: number
  maxItems?: number
  anyOf?: BlenderInputSchema[]
  enum?: unknown[]
  examples?: unknown[]
  description?: string
  "x-blender-validation"?: string
}

const schemas: Record<string, BlenderInputSchema> = generated.tools
const validators = new Map<string, z.ZodTypeAny>()

function validator(schema: BlenderInputSchema): z.ZodTypeAny {
  if (schema.anyOf) {
    const variants = schema.anyOf.map(validator)
    return z.union(variants as [z.ZodTypeAny, z.ZodTypeAny, ...z.ZodTypeAny[]])
  }
  if (schema.enum) return z.unknown().refine(value => schema.enum!.includes(value), "Unknown enum value")
  switch (schema.type) {
    case "string": return z.string()
    case "number": return z.number().finite()
    case "integer": return z.number().int().finite()
    case "boolean": return z.boolean()
    case "null": return z.null()
    case "array": {
      let result = z.array(schema.items ? validator(schema.items) : z.unknown())
      if (schema.minItems !== undefined) result = result.min(schema.minItems)
      if (schema.maxItems !== undefined) result = result.max(schema.maxItems)
      return result
    }
    case "object": {
      if (!schema.properties) return z.record(z.unknown())
      const shape = Object.fromEntries(Object.entries(schema.properties).map(([key, value]) => {
        const item = validator(value)
        return [key, schema.required?.includes(key) ? item.refine(value => value !== undefined, "Required") : item.optional()]
      }))
      return schema.additionalProperties ? z.object(shape).passthrough() : z.object(shape).strict()
    }
    default: return z.unknown()
  }
}

export function getBlenderToolInputSchema(name: string): BlenderInputSchema {
  if (!Object.hasOwn(schemas, name)) throw new Error(`No input schema for Blender tool: ${name}`)
  const schema = schemas[name]
  return structuredClone(schema)
}

export function validateBlenderToolArguments(name: string, params: Record<string, unknown>): void {
  let compiled = validators.get(name)
  if (!compiled) {
    compiled = validator(getBlenderToolInputSchema(name))
    validators.set(name, compiled)
  }
  const result = compiled.safeParse(params)
  if (!result.success) {
    const issues = result.error.issues.slice(0, 5).map(issue => `${issue.path.join(".") || "params"}: ${issue.message}`)
    throw new Error(`Invalid arguments for ${name}: ${issues.join("; ")}`)
  }
}
