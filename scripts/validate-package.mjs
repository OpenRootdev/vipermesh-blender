import assert from "node:assert/strict"
import fs from "node:fs"
import { execFileSync } from "node:child_process"

const packageJson = JSON.parse(fs.readFileSync("package.json", "utf8"))
const cliPath = packageJson.bin?.["vipermesh-blender"]
assert.equal(typeof cliPath, "string", "package.json must expose vipermesh-blender")
assert.ok(fs.existsSync(cliPath), `Missing built CLI: ${cliPath}`)

const cli = fs.readFileSync(cliPath, "utf8")
assert.ok(cli.startsWith("#!/usr/bin/env node"), "Built CLI must retain its Node shebang")
assert.ok(fs.existsSync("skills/using-vipermesh-blender/SKILL.md"))
for (const reference of ["scene-operations", "spatial-validation", "visual-presentation", "geometry-materials-assets", "character-animation-export"]) {
  assert.ok(fs.existsSync(`skills/using-vipermesh-blender/references/${reference}.md`), `Missing shipped reference: ${reference}`)
}
assert.ok(!fs.existsSync("data/tool-guides"))
assert.ok(fs.existsSync("addon/vipermesh-addon.py"))
const catalogCli = packageJson.bin?.["vipermesh-assets"]
assert.equal(typeof catalogCli, "string")
assert.ok(fs.readFileSync(catalogCli, "utf8").startsWith("#!/usr/bin/env node"))
assert.ok(fs.existsSync("NOTICE.md"))
assert.ok(fs.existsSync("SECURITY.md"))
if (process.env.npm_execpath) {
  const [packed] = JSON.parse(execFileSync(process.execPath,
    [process.env.npm_execpath, "pack", "--dry-run", "--json", "--ignore-scripts"], { encoding: "utf8" }))
  const paths = packed.files.map(file => file.path)
  for (const required of [cliPath, catalogCli, "addon/vipermesh-addon.py", "NOTICE.md", "SECURITY.md"]) {
    assert.ok(paths.includes(required.replace(/^\.\//, "")), `Required file missing from package: ${required}`)
  }
  assert.ok(!paths.some(file => file.includes("__pycache__") || file.endsWith(".pyc")), "Do not ship local Python bytecode")
}

console.log("ViperMesh package contents are valid")
