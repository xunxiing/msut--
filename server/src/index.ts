import 'dotenv/config'
import express from 'express'
import cookieParser from 'cookie-parser'
import helmet from 'helmet'
import path from 'node:path'
import { register, login, logout, me, authGuard } from './auth.js'
import {
  createResource, uploadToResource, upload, getResource, listResources, downloadFile
} from './files.js'

const app = express()
app.use(helmet({ crossOriginResourcePolicy: false }))
app.use(express.json())
app.use(cookieParser())

// 静态文件（公开访问）
app.use('/uploads', express.static(path.resolve(process.cwd(), 'uploads'), {
  maxAge: '365d',
  immutable: true
}))

// 鉴权路由
app.post('/api/auth/register', register)
app.post('/api/auth/login', login)
app.post('/api/auth/logout', logout)
app.get('/api/auth/me', me)

// 示例受保护接口
app.get('/api/private/ping', authGuard, (_req: any, res: any) => {
  res.json({ pong: true })
})

// 资源与文件路由
app.post('/api/resources', authGuard, createResource)
app.get('/api/resources', listResources)
app.get('/api/resources/:slug', getResource)

app.post('/api/files/upload', authGuard, upload.array('files', 10), uploadToResource)
app.get('/api/files/:id/download', downloadFile)

const port = Number(process.env.PORT || 3000)
app.listen(port, () => {
  console.log(`Auth server listening on http://localhost:${port}`)
})
