#!/usr/bin/env node
import { mkdirSync, readdirSync, statSync, writeFileSync, existsSync, openSync, closeSync, fsyncSync, renameSync, unlinkSync } from "fs"
import path from "path"
import { createHash, randomUUID } from "node:crypto"
import { fileURLToPath } from "node:url"
import {
  LocalAssetCatalogSchema,
  type LocalAssetCatalog,
  type LocalAssetEntry,
  loadLocalAssetCatalog,
  slugifyLocalAssetId,
  titleCaseFromSlug,
} from "../../lib/assets/local-catalog"

const SUPPORTED_ASSET_EXTENSIONS = new Set([".blend", ".glb", ".gltf", ".fbx", ".obj"])
const SUPPORTED_PREVIEW_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp"]
const EXCLUDED_ROOT_DIRECTORIES = new Set(["catalog", "incoming", "previews", "cache"])

interface CliOptions {
  root: string
  out: string
}

function parseArgs(argv: string[]): CliOptions {
  let root = ""
  let out = ""

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index]
    if (arg === "--help" || arg === "-h") {
      console.log('Usage: vipermesh-assets --root <curated-library-folder> [--out <catalog.json>]')
      process.exit(0)
    }
    if (arg === "--root") {
      root = argv[index + 1] ?? ""
      index += 1
    } else if (arg === "--out") {
      out = argv[index + 1] ?? ""
      index += 1
    } else {
      throw new Error(`Unknown option: ${arg}`)
    }
  }

  if (!root) {
    throw new Error("Missing required --root <asset-library-folder> argument")
  }

  const resolvedRoot = path.resolve(root)
  const resolvedOut = out
    ? path.resolve(out)
    : path.join(resolvedRoot, "catalog", "assets.json")

  return { root: resolvedRoot, out: resolvedOut }
}

function walkFiles(dir: string): string[] {
  const entries = readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name < b.name ? -1 : a.name > b.name ? 1 : 0)
  const files: string[] = []

  for (const entry of entries) {
    if (entry.name.startsWith(".")) continue
    const fullPath = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      if (entry.name.startsWith(".") || EXCLUDED_ROOT_DIRECTORIES.has(entry.name.toLowerCase())) {
        continue
      }
      files.push(...walkFiles(fullPath))
      continue
    }

    if (!entry.isFile()) continue
    const extension = path.extname(entry.name).toLowerCase()
    if (SUPPORTED_ASSET_EXTENSIONS.has(extension)) {
      files.push(fullPath)
    }
  }

  return files
}

function toPosixPath(value: string): string {
  return value.split(path.sep).join("/")
}

function normalizeCatalogPath(value: string): string {
  const normalized = toPosixPath(path.normalize(value)).replace(/^\.\//, "")
  return process.platform === "win32" ? normalized.toLowerCase() : normalized
}

function dedupeStrings(values: Array<string | undefined>): string[] {
  return Array.from(
    new Set(
      values
        .map((value) => value?.trim())
        .filter((value): value is string => Boolean(value && value.length > 1))
    )
  )
}

function buildGeneratedTags(directoryParts: string[], basename: string): string[] {
  const tags = [...directoryParts, ...basename.split(/[-_ ]+/)]
    .map(slugifyLocalAssetId)
    .filter((tag) => tag.length > 1)

  return Array.from(new Set(tags))
}

function deriveCategory(directoryParts: string[]): string {
  const normalizedParts = directoryParts.map(slugifyLocalAssetId).filter(Boolean)
  if (normalizedParts.length === 0) {
    return "uncategorized"
  }

  const [rootGroup, nextGroup, lastGroup] = normalizedParts
  if (rootGroup === "props") {
    return nextGroup || lastGroup || "uncategorized"
  }

  return lastGroup || "uncategorized"
}

function findPreviewPath(assetPath: string): string | undefined {
  const baseWithoutExtension = assetPath.slice(0, assetPath.length - path.extname(assetPath).length)
  for (const extension of SUPPORTED_PREVIEW_EXTENSIONS) {
    const previewPath = `${baseWithoutExtension}${extension}`
    if (existsSync(previewPath)) {
      return previewPath
    }
  }
  return undefined
}

function buildExistingAssetIndex(catalogPath: string, root: string): Map<string, LocalAssetEntry> {
  if (!existsSync(catalogPath)) {
    return new Map()
  }

  const existingCatalog = loadLocalAssetCatalog(catalogPath)
  const result = new Map<string, LocalAssetEntry>()
  for (const asset of existingCatalog.assets) {
    const key = normalizeCatalogPath(path.isAbsolute(asset.import_spec.file_path)
      ? path.relative(root, asset.import_spec.file_path) : asset.import_spec.file_path)
    if (result.has(key)) throw new Error(`Duplicate catalog file path: ${key}`)
    result.set(key, asset)
  }
  return result
}

function mergeWithExistingAsset(
  generatedAsset: LocalAssetEntry,
  existingAsset?: LocalAssetEntry
): LocalAssetEntry {
  if (!existingAsset) {
    return generatedAsset
  }

  const existingTags = Array.isArray(existingAsset.tags) ? existingAsset.tags : []
  const generatedTags = Array.isArray(generatedAsset.tags) ? generatedAsset.tags : []

  return {
    ...generatedAsset,
    ...existingAsset,
    name: existingAsset.name?.trim() || generatedAsset.name,
    tags: dedupeStrings([...existingTags, ...generatedTags]),
    style: existingAsset.style ?? generatedAsset.style,
    description: existingAsset.description ?? generatedAsset.description,
    license: existingAsset.license ?? generatedAsset.license,
    source: existingAsset.source ?? generatedAsset.source,
    source_url: existingAsset.source_url ?? generatedAsset.source_url,
    preview_path: existingAsset.preview_path ?? generatedAsset.preview_path,
    quality_score: existingAsset.quality_score ?? generatedAsset.quality_score,
    validated_blender_version:
      existingAsset.validated_blender_version ?? generatedAsset.validated_blender_version,
    dimensions_m: existingAsset.dimensions_m ?? generatedAsset.dimensions_m,
    import_spec: {
      ...existingAsset.import_spec,
      ...generatedAsset.import_spec,
      append_type: existingAsset.import_spec.append_type ?? generatedAsset.import_spec.append_type,
      asset_names: existingAsset.import_spec.asset_names ?? generatedAsset.import_spec.asset_names,
    },
  }
}

function buildCatalog(root: string, outPath: string): LocalAssetCatalog {
  const assetFiles = walkFiles(root)
  const existingAssets = buildExistingAssetIndex(outPath, root)
  const previous = existsSync(outPath) ? loadLocalAssetCatalog(outPath) : undefined
  const assets = assetFiles.map((filePath) => {
    const relativePath = path.relative(root, filePath)
    const directoryParts = path.dirname(relativePath) === "."
      ? []
      : path.dirname(relativePath).split(path.sep).filter(Boolean)
    const extension = path.extname(filePath).toLowerCase()
    const format = extension.slice(1) as "blend" | "glb" | "gltf" | "fbx" | "obj"
    const basename = path.basename(relativePath, extension)
    const basenameId = slugifyLocalAssetId(basename) || `asset-${createHash("sha256").update(relativePath).digest("hex").slice(0, 12)}`
    const idParts = [...directoryParts.map(slugifyLocalAssetId).filter(Boolean), basenameId]
    const tags = buildGeneratedTags(directoryParts, basename)
    const category = deriveCategory(directoryParts)
    const previewPath = findPreviewPath(filePath)
    const catalogFilePath = toPosixPath(relativePath)
    const existingAsset = existingAssets.get(normalizeCatalogPath(catalogFilePath))

    const generatedAsset: LocalAssetEntry = {
      id: idParts.join("/"),
      name: titleCaseFromSlug(basename),
      category: slugifyLocalAssetId(category) || "uncategorized",
      tags,
      style: "",
      description: "",
      license: "",
      source: "user-curated",
      preview_path: previewPath ? toPosixPath(path.relative(root, previewPath)) : undefined,
      import_spec: {
        file_path: catalogFilePath,
        format,
        ...(format === "blend"
          ? { append_type: "collections" as const, asset_names: [] }
          : {}),
      },
    }

    existingAssets.delete(normalizeCatalogPath(catalogFilePath))
    return mergeWithExistingAsset(generatedAsset, existingAsset)
  })

  // Do not silently delete manually curated/offline entries during a refresh.
  assets.push(...existingAssets.values())
  const ids = new Set<string>()
  for (const asset of assets) {
    if (!asset.id || ids.has(asset.id)) throw new Error(`Duplicate or empty asset ID: ${asset.id}`)
    ids.add(asset.id)
  }
  return LocalAssetCatalogSchema.parse({
    ...previous,
    version: 1,
    generated_at: new Date().toISOString(),
    library_root: root,
    assets: assets.sort((a, b) => a.id.localeCompare(b.id)),
  })
}

export function refreshLocalAssetCatalog(root: string, output?: string): LocalAssetCatalog {
  root = path.resolve(root)
  const out = output ? path.resolve(output) : path.join(root, "catalog", "assets.json")
  if (!statSync(root).isDirectory()) throw new Error(`Asset root is not a directory: ${root}`)
  mkdirSync(path.dirname(out), { recursive: true })
  const lock = `${out}.lock`
  const lockFd = openSync(lock, "wx")
  const temporary = `${out}.${randomUUID()}.tmp`
  try {
    const catalog = buildCatalog(root, out)
    const fd = openSync(temporary, "wx")
    try {
      writeFileSync(fd, `${JSON.stringify(catalog, null, 2)}\n`, "utf8")
      fsyncSync(fd)
    } finally { closeSync(fd) }
    renameSync(temporary, out)
    return catalog
  } finally {
    if (existsSync(temporary)) unlinkSync(temporary)
    closeSync(lockFd)
    unlinkSync(lock)
  }
}

function main() {
  const options = parseArgs(process.argv.slice(2))
  const rootStats = statSync(options.root)
  if (!rootStats.isDirectory()) {
    throw new Error(`Asset root is not a directory: ${options.root}`)
  }

  const catalog = refreshLocalAssetCatalog(options.root, options.out)

  const blendAssetsNeedingNames = catalog.assets.filter(
    (asset) => asset.import_spec.format === "blend" && (asset.import_spec.asset_names?.length ?? 0) === 0
  ).length

  console.log(`[LocalAssets] Wrote catalog with ${catalog.assets.length} assets to ${options.out}`)
  console.log("[LocalAssets] Indexed curated assets only; raw intake folders under incoming/ are skipped.")
  if (blendAssetsNeedingNames > 0) {
    console.log(
      `[LocalAssets] ${blendAssetsNeedingNames} .blend entries still use the default first-collection import fallback; add import_spec.asset_names for precise imports.`
    )
  }
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) main()
