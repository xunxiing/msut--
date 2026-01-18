import axios from 'axios'

export type MeLoveallFileInfo = {
  name: string
  full_name: string
  size: string
  size_bytes: number
  date: string
  preview_url: string | null
  download_url: string | null
}

export type MeLoveallListResponse =
  | { success: true; count: number; files: MeLoveallFileInfo[] }
  | { success: false; error: string }

export type MeLoveallInfoResponse =
  | { success: true; file: MeLoveallFileInfo }
  | { success: false; error: string }

const API_BASE = 'https://me.loveall.icu/api.php'

function buildApiUrl(params: Record<string, string>) {
  const url = new URL(API_BASE)
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v)
  return url.toString()
}

export function meLoveallPreviewUrl(fileName: string) {
  return buildApiUrl({ action: 'preview', file: fileName })
}

export function meLoveallDownloadUrl(fileName: string) {
  return buildApiUrl({ action: 'download', file: fileName })
}

export async function getMeLoveallResourceInfo(fileName: string) {
  const { data } = await axios.get<MeLoveallInfoResponse>(API_BASE, {
    params: { action: 'info', file: fileName },
  })

  if (!data || typeof data !== 'object') {
    throw new Error('外站 API 返回异常')
  }
  if (data.success) return data.file
  throw new Error(data.error || '外站资源不存在')
}

export async function listMeLoveallResources() {
  const { data } = await axios.get<MeLoveallListResponse>(API_BASE, {
    params: { action: 'list' },
  })

  if (!data || typeof data !== 'object') {
    throw new Error('外站 API 返回异常')
  }
  if (data.success) return { count: data.count, files: data.files || [] }
  throw new Error(data.error || '外站资源列表获取失败')
}
