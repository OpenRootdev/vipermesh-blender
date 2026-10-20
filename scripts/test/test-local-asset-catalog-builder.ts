import assert from "node:assert/strict"
import fs from "node:fs"
import os from "node:os"
import path from "node:path"
import { refreshLocalAssetCatalog } from "../maintenance/build-local-asset-catalog"

const root = fs.mkdtempSync(path.join(os.tmpdir(), "vipermesh-catalog-test-"))
try {
  for (const folder of ["props", "cache", "incoming", ".hidden"]) {
    fs.mkdirSync(path.join(root, folder))
    fs.writeFileSync(path.join(root, folder, `${folder}.glb`), "fixture")
  }
  const out = path.join(root, "catalog/assets.json")
  const first = refreshLocalAssetCatalog(root, out)
  assert.equal(first.assets.length, 1)
  first.assets[0].id = "my-stable-id"
  first.assets[0].name = "Artist's name"
  first.assets[0].category = "custom-category"
  first.assets[0].tags = ["reviewed"]
  first.assets[0].editorial_note = "Keep this unknown field"
  first.assets[0].import_spec.custom_setting = true
  fs.writeFileSync(out, JSON.stringify(first))
  const next = refreshLocalAssetCatalog(root, out)
  assert.equal(next.assets[0].id, "my-stable-id")
  assert.equal(next.assets[0].category, "custom-category")
  assert.equal(next.assets[0].editorial_note, "Keep this unknown field")
  assert.equal(next.assets[0].import_spec.custom_setting, true)
  assert.ok(next.assets[0].tags.includes("reviewed"))
  fs.writeFileSync(path.join(root, "props/\u63a2\u9488.glb"), "Unicode filename")
  fs.unlinkSync(path.join(root, "props/props.glb"))
  const offline = refreshLocalAssetCatalog(root, out)
  assert.ok(offline.assets.some(asset => asset.id === "my-stable-id"), "Retain offline curated entries")
  const unicode = offline.assets.find(asset => asset.import_spec.file_path.endsWith("\u63a2\u9488.glb"))
  assert.ok(unicode?.id)
  assert.ok(unicode?.name.includes("\u63a2\u9488"))
  const again = refreshLocalAssetCatalog(root, out)
  assert.equal(again.assets.find(asset => asset.import_spec.file_path.endsWith("\u63a2\u9488.glb"))?.id, unicode.id)
  const before = fs.readFileSync(out, "utf8")
  fs.writeFileSync(`${out}.lock`, "other writer")
  assert.throws(() => refreshLocalAssetCatalog(root, out), /refresh|EEXIST/i)
  assert.equal(fs.readFileSync(out, "utf8"), before)
  fs.unlinkSync(`${out}.lock`)
  fs.writeFileSync(out, JSON.stringify({ ...offline, assets: [...offline.assets,
    { ...offline.assets[0], id: "different-id-same-file" }] }))
  const duplicate = fs.readFileSync(out, "utf8")
  assert.throws(() => refreshLocalAssetCatalog(root, out), /duplicate.*path/i)
  assert.equal(fs.readFileSync(out, "utf8"), duplicate)
  fs.writeFileSync(out, "broken JSON")
  assert.throws(() => refreshLocalAssetCatalog(root, out))
  assert.equal(fs.readFileSync(out, "utf8"), "broken JSON")
  fs.unlinkSync(out)
  fs.writeFileSync(path.join(root, "props/props.glb"), "fixture")
  fs.writeFileSync(path.join(root, "props/props.blend"), "same generated ID")
  assert.throws(() => refreshLocalAssetCatalog(root, out), /duplicate.*id/i)
  assert.ok(!fs.existsSync(out))
  assert.ok(!fs.existsSync(`${out}.lock`))
  console.log("Local asset catalog builder checks passed")
} finally { fs.rmSync(root, { recursive: true, force: true }) }
