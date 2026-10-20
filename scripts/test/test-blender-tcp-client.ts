import assert from "node:assert/strict"
import net from "node:net"
import { BlenderMcpClient } from "../../lib/mcp/client"

async function main() {
  const sockets = new Set<net.Socket>()
  let mode = "close"
  const server = net.createServer(socket => {
    sockets.add(socket)
    socket.on("close", () => sockets.delete(socket))
    socket.on("error", () => undefined)
    socket.on("data", () => {
      if (mode === "close") socket.end('{"status":')
      if (mode === "ok") socket.write('{"status":"success","result":{}}')
      if (mode === "wrong-id") socket.write('{"status":"success","id":"wrong-request"}')
    })
  })
  await new Promise<void>(resolve => server.listen(0, "127.0.0.1", resolve))
  const port = (server.address() as net.AddressInfo).port
  const client = new BlenderMcpClient({ host: "127.0.0.1", port, timeoutMs: 100 })
  const bounded = <T>(promise: Promise<T>) => Promise.race([promise, new Promise<never>((_, reject) => {
    const timer = setTimeout(() => reject(new Error("Request did not settle")), 500)
    promise.then(() => clearTimeout(timer), () => clearTimeout(timer))
  })])
  try {
    await assert.rejects(bounded(client.execute({ type: "get_scene_info" })), /closed/i)
    mode = "ok"
    assert.equal((await bounded(client.execute({ type: "get_scene_info" }))).status, "success")
    await new Promise(resolve => setTimeout(resolve, 150))
    assert.equal(sockets.size, 1, "Reasoning pauses must not discard an idle connection")
    mode = "timeout"
    await assert.rejects(bounded(client.execute({ type: "get_scene_info" })), /timed out/i)
    mode = "wrong-id"
    await assert.rejects(bounded(client.execute({ type: "get_scene_info" })), /id mismatch/i)
    await client.close()
    console.log("Blender TCP client checks passed")
  } finally {
    for (const socket of sockets) socket.destroy()
    await new Promise<void>(resolve => server.close(() => resolve()))
  }
}
main().catch(error => { console.error(error); process.exitCode = 1 })
