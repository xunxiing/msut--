import axios from 'axios'

export type ExternalFileInfo = {
  name: string
  size: string
  date: string
  preview_url: string | null
  download_url: string
}

export type ExternalListResponse = {
  total: number
  page: number
  pageSize: number
  files: ExternalFileInfo[]
}

export type ExternalInfoResponse = {
  file: ExternalFileInfo
}

const API_BASE = 'https://m.mgw.os.kg/api.php'

function buildApiUrl(params: Record<string, string>) {
  const url = new URL(API_BASE)
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v)
  return url.toString()
}

export function externalPreviewUrl(fileId: string) {
  return buildApiUrl({ action: 'preview', file: fileId })
}

export function externalDownloadUrl(fileId: string) {
  return buildApiUrl({ action: 'download', file: fileId })
}

export async function getExternalResourceInfo(fileId: string) {
  const { data } = await axios.get<ExternalInfoResponse>(API_BASE, {
    params: { action: 'info', file: fileId },
  })
  if (!data || !data.file) {
    throw new Error('资源不存在')
  }
  return data.file
}

export async function listExternalResources(opts?: {
  page?: number
  pageSize?: number
  sort?: 'date' | 'random'
  order?: 'asc' | 'desc'
  search?: string
}) {
  const params: Record<string, string> = { action: 'list' }
  if (opts?.page) params.page = String(opts.page)
  if (opts?.pageSize) params.pageSize = String(opts.pageSize)
  if (opts?.sort) params.sort = opts.sort
  if (opts?.order) params.order = opts.order
  if (opts?.search) params.search = opts.search

  const { data } = await axios.get<ExternalListResponse>(API_BASE, { params })
  if (!data || !Array.isArray(data.files)) {
    throw new Error('资源列表获取失败')
  }
  return data
}
