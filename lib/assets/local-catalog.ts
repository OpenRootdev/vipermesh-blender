import { existsSync, readFileSync } from "fs"
import path from "path"
import { z } from "zod"

export const LocalAssetImportFormatSchema = z.enum(["blend", "glb", "gltf", "fbx", "obj"])

export const LocalAssetImportSpecSchema = z.object({
  file_path: z.string().min(1),
  format: LocalAssetImportFormatSchema.optional(),
  append_type: z.enum(["collection", "collections", "object", "objects"]).optional(),
  asset_names: z.array(z.string().min(1)).optional(),
}).passthrough()

export const LocalAssetEntrySchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  category: z.string().min(1),
  tags: z.array(z.string()).default([]),
  style: z.string().optional(),
  description: z.string().optional(),
  license: z.string().optional(),
  source: z.string().optional(),
  source_url: z.string().url().optional(),
  preview_path: z.string().optional(),
  quality_score: z.number().min(0).max(1).optional(),
  validated_blender_version: z.string().optional(),
  dimensions_m: z.array(z.number()).length(3).optional(),
  import_spec: LocalAssetImportSpecSchema,
}).passthrough()

export const LocalAssetCatalogSchema = z.object({
  version: z.number().int().positive(),
  generated_at: z.string().optional(),
  library_root: z.string().optional(),
  assets: z.array(LocalAssetEntrySchema),
}).passthrough()

export type LocalAssetCatalog = z.infer<typeof LocalAssetCatalogSchema>
export type LocalAssetEntry = z.infer<typeof LocalAssetEntrySchema>

export function slugifyLocalAssetId(input: string): string {
  return input
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
}

export function titleCaseFromSlug(input: string): string {
  return input
    .split(/[-_]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ")
}

export function resolveCatalogRelativePath(baseDir: string, targetPath?: string): string | undefined {
  if (!targetPath) return undefined
  if (path.isAbsolute(targetPath)) return path.normalize(targetPath)
  return path.normalize(path.join(baseDir, targetPath))
}

export function loadLocalAssetCatalog(catalogPath: string): LocalAssetCatalog {
  const resolvedPath = path.resolve(catalogPath)
  if (!existsSync(resolvedPath)) {
    throw new Error(`Catalog file not found: ${resolvedPath}`)
  }

  const raw = readFileSync(resolvedPath, "utf-8")
  const parsed = JSON.parse(raw) as unknown
  return LocalAssetCatalogSchema.parse(parsed)
}
