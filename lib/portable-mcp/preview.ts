import { open } from "node:fs/promises"

export const MAX_PREVIEW_IMAGE_BYTES = 3 * 1024 * 1024

export async function readPreviewImage(filepath: string) {
  let file
  try {
    file = await open(filepath, "r")
    const stats = await file.stat()
    if (!stats.isFile() || stats.size === 0 || stats.size > MAX_PREVIEW_IMAGE_BYTES) return undefined
    const buffer = Buffer.alloc(stats.size)
    const { bytesRead } = await file.read(buffer, 0, buffer.length, 0)
    if (bytesRead !== buffer.length) return undefined
    const mimeType = buffer.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))
      ? "image/png"
      : buffer[0] === 255 && buffer[1] === 216 && buffer[2] === 255
        ? "image/jpeg" : undefined
    if (!mimeType) return undefined
    return { type: "image" as const, mimeType, data: buffer.toString("base64") }
  } catch {
    return undefined
  } finally {
    await file?.close()
  }
}
