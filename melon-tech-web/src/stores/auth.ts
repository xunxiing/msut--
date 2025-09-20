import { defineStore } from 'pinia'
import { http } from '../api/http'

type User = { id: number; email: string; name: string } | null

export const useAuth = defineStore('auth', {
  state: () => ({ user: null as User, loading: false, error: '' as string | null }),
  actions: {
    async fetchMe() {
      const { data } = await http.get('/auth/me')
      this.user = data.user
    },
    async register(payload: { email: string; password: string; name: string }) {
      this.loading = true
      this.error = null
      try {
        const { data } = await http.post('/auth/register', payload)
        this.user = data.user
      } catch (e: any) {
        this.error = e?.response?.data?.error || '注册失败'
        throw e
      } finally { this.loading = false }
    },
    async login(payload: { email: string; password: string }) {
      this.loading = true
      this.error = null
      try {
        const { data } = await http.post('/auth/login', payload)
        this.user = data.user
      } catch (e: any) {
        this.error = e?.response?.data?.error || '登录失败'
        throw e
      } finally { this.loading = false }
    },
    async logout() {
      await http.post('/auth/logout')
      this.user = null
    }
  }
})
