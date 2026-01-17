import { defineStore } from 'pinia'
import { http } from '../api/http'

type User = { id: number; username: string; name: string } | null

export const useAuth = defineStore('auth', {
  state: () => ({ user: null as User, loading: false, error: '' as string | null }),
  actions: {
    async fetchMe() {
      try {
        const { data } = await http.get('/auth/me')
        if (data.user) {
          this.user = data.user
          return
        }
        await this.refresh()
      } catch {
        this.user = null
      }
    },
    async register(payload: { username: string; password: string; name: string }) {
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
    async login(payload: { username: string; password: string; remember?: boolean }) {
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
    },
    async refresh() {
      try {
        const { data } = await http.post('/auth/refresh')
        this.user = data.user
      } catch {
        this.user = null
      }
    }
  }
})
