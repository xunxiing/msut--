import type { AxiosResponse } from 'axios'
import { http } from './http'

export function generateMelsave(dsl: string): Promise<AxiosResponse<Blob>> {
  return http.post('/melsave/generate', { dsl }, { responseType: 'blob' })
}

