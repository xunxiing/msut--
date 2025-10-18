import { http } from './http'

export async function checkWatermark(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  const resp = await http.post('/watermark/check', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return resp.data as {
    watermark: number
    length: number
    embedded: number | null
    matches: Array<{
      fileId: number
      resourceId: number | null
      resourceSlug: string | null
      resourceTitle: string | null
      originalName: string
      urlPath: string
    }>
  }
}

