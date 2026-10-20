import net from "net"
import { randomUUID } from "crypto"
import { getMcpConfig } from "./config"
import { McpCommand, McpResponse } from "./types"

export interface LocalAssetLibraryStatus {
  enabled?: boolean
  message?: string
  catalog_path?: string
  library_root?: string
  managed_cache_root?: string
  asset_count?: number
  catalog_version?: number
}

export class BlenderMcpClient {
  private socket: net.Socket | null = null
  private connected = false
  private executionTail: Promise<void> = Promise.resolve()

  constructor(private readonly config = getMcpConfig()) {}

  /**
   * Establish a socket connection to the Blender MCP server.
   * Connection is memoized per client instance.
   */
  private async ensureConnection() {
    if (this.connected && this.socket && !this.socket.destroyed) {
      return this.socket
    }

    const { host, port, timeoutMs } = this.config

    this.socket = await new Promise<net.Socket>((resolve, reject) => {
      const socket = net.createConnection({ host, port }, () => {
        socket.setTimeout(0)
        this.connected = true
        resolve(socket)
      })

      socket.setTimeout(timeoutMs, () => {
        socket.destroy(new Error("Blender MCP connection timed out"))
      })

      socket.once("error", (error) => {
        reject(error)
      })
    })

    const connectedSocket = this.socket
    connectedSocket.on("close", () => {
      if (this.socket === connectedSocket) {
        this.connected = false
        this.socket = null
      }
    })

    return this.socket
  }

  /**
   * Send a command to the Blender MCP server.
   * NOTE: The final implementation will include structured payloads and response parsing.
   */
  async execute<T = unknown>(command: McpCommand): Promise<McpResponse<T>> {
    const result = this.executionTail.then(() => this.executeSerialized<T>(command))
    this.executionTail = result.then(() => undefined, () => undefined)
    return result
  }

  private async executeSerialized<T = unknown>(command: McpCommand): Promise<McpResponse<T>> {
    const socket = await this.ensureConnection()

    const request = {
      ...command,
      id: command.id ?? randomUUID(),
    }
    const payload = JSON.stringify(request)

    const response = await new Promise<string>((resolve, reject) => {
      const chunks: Buffer[] = []

      const onData = (chunk: Buffer) => {
        chunks.push(chunk)
        const raw = Buffer.concat(chunks).toString("utf8")
        try {
          const parsed = JSON.parse(raw) as { id?: unknown }
          if (parsed.id !== undefined && parsed.id !== request.id) {
            onError(new Error("Blender MCP response id mismatch"))
            socket.destroy()
            return
          }
          cleanup()
          resolve(raw)
        } catch {
          // Blender responses are unframed JSON, so keep reading until a full
          // document parses. Calls are serialized to prevent response overlap.
        }
      }

      const onError = (error: Error) => {
        cleanup()
        reject(error)
      }

      const onTimeout = () => {
        onError(new Error("Timed out while waiting for Blender MCP response"))
        socket.destroy()
      }
      const onClose = () => onError(new Error("Blender MCP connection closed before a complete response"))
      const timer = setTimeout(onTimeout, this.config.timeoutMs)

      const cleanup = () => {
        clearTimeout(timer)
        socket.off("data", onData)
        socket.off("error", onError)
        socket.off("timeout", onTimeout)
        socket.off("close", onClose)
      }

      socket.once("error", onError)
      socket.once("timeout", onTimeout)
      socket.once("close", onClose)
      socket.on("data", onData)
      socket.write(`${payload}\n`)
    })

    try {
      const parsed = JSON.parse(response) as McpResponse<T>
      return {
        ...parsed,
        raw: parsed.raw ?? response,
      }
    } catch {
      return {
        status: "error",
        message: "Failed to parse Blender MCP response",
        raw: response,
      }
    }
  }

  async close() {
    await this.executionTail
    if (!this.socket) return
    const socket = this.socket
    this.socket = null
    this.connected = false
    if (socket.destroyed) return
    await new Promise<void>((resolve) => {
      const finish = () => { socket.off("close", finish); resolve() }
      socket.once("close", finish)
      socket.end(finish)
    })
    socket.destroy()
  }
}

export function createMcpClient() {
  return new BlenderMcpClient()
}

let sharedMcpClient: BlenderMcpClient | undefined

/** Process-lifetime client for serialized agent and middleware tool traffic. */
export function getSharedMcpClient() {
  sharedMcpClient ??= createMcpClient()
  return sharedMcpClient
}

export async function closeSharedMcpClient() {
  const client = sharedMcpClient
  sharedMcpClient = undefined
  await client?.close()
}

export async function getLocalAssetLibraryStatus() {
  const client = createMcpClient()
  try {
    const response = await client.execute<LocalAssetLibraryStatus>({
      type: "get_local_asset_library_status",
      params: {},
    })

    if (response.status === "ok" || response.status === "success") {
      const result = response.result ?? {}
      return {
        enabled: Boolean(result.enabled),
        message:
          typeof result.message === "string"
            ? result.message
            : result.enabled
              ? "Local asset library enabled"
              : "Local asset library disabled",
        catalogPath:
          typeof result.catalog_path === "string" ? result.catalog_path : undefined,
        libraryRoot:
          typeof result.library_root === "string" ? result.library_root : undefined,
        managedCacheRoot:
          typeof result.managed_cache_root === "string" ? result.managed_cache_root : undefined,
        assetCount:
          typeof result.asset_count === "number" ? result.asset_count : undefined,
        catalogVersion:
          typeof result.catalog_version === "number" ? result.catalog_version : undefined,
        raw: result,
      }
    }

    return {
      enabled: false,
      message: response.message ?? "Local asset library status probe failed",
      raw: response,
    }
  } catch (error) {
    return {
      enabled: false,
      message: error instanceof Error ? error.message : String(error),
      raw: null,
    }
  } finally {
    await client.close().catch(() => undefined)
  }
}

export async function checkMcpConnection() {
  const config = getMcpConfig()

  return new Promise<{ connected: boolean; error?: string }>((resolve) => {
    const socket = net.createConnection(
      { host: config.host, port: config.port },
      () => {
        // TCP connected — now verify the Blender addon is actually responding
        // by sending a lightweight MCP command and checking for a valid JSON response
        const probe = JSON.stringify({
          id: randomUUID(),
          type: "get_all_object_info",
          params: {},
        })

        const chunks: Buffer[] = []
        const timeout = setTimeout(() => {
          socket.destroy()
          resolve({ connected: false, error: "Blender addon did not respond to probe" })
        }, Math.min(5_000, config.timeoutMs))

        socket.on("data", (chunk: Buffer) => {
          chunks.push(chunk)
          const raw = Buffer.concat(chunks).toString("utf8")
          if (raw.trim().endsWith("}")) {
            clearTimeout(timeout)
            socket.end()
            try {
              const parsed = JSON.parse(raw)
              // Valid MCP response from the addon
              if (parsed.status || parsed.result !== undefined) {
                resolve({ connected: true })
              } else {
                resolve({ connected: false, error: "Unexpected response from port" })
              }
            } catch {
              resolve({ connected: false, error: "Non-JSON response — not the Blender addon" })
            }
          }
        })

        socket.once("error", (error) => {
          clearTimeout(timeout)
          resolve({
            connected: false,
            error: error instanceof Error ? error.message : String(error),
          })
        })

        socket.write(`${probe}\n`)
      }
    )

    socket.setTimeout(Math.min(5_000, config.timeoutMs), () => {
      socket.destroy()
      resolve({
        connected: false,
        error: "Connection timed out",
      })
    })

    socket.once("error", (error) => {
      resolve({
        connected: false,
        error: error instanceof Error ? error.message : String(error),
      })
    })
  })
}
