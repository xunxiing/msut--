import type { Request, Response, NextFunction } from 'express'
import { db } from './db.js'
import bcrypt from 'bcryptjs'
import jwt from 'jsonwebtoken'
import { z } from 'zod'
import type { User, JWTPayload } from './types.d.js'

const registerSchema = z.object({
  username: z.string().min(3).max(32),
  password: z.string().min(6).max(72),
  name: z.string().min(1).max(32)
})

const loginSchema = z.object({
  username: z.string().min(3).max(32),
  password: z.string().min(6).max(72)
})

// 类型保护函数：验证数据库查询结果是否为 User 类型
function isUser(data: unknown): data is User {
  return (
    typeof data === 'object' &&
    data !== null &&
    'id' in data && typeof (data as User).id === 'number' &&
    'username' in data && typeof (data as User).username === 'string' &&
    'name' in data && typeof (data as User).name === 'string' &&
    'password_hash' in data && typeof (data as User).password_hash === 'string'
  )
}

const JWT_SECRET = process.env.JWT_SECRET || 'dev'

// 环境变量解析函数
const fromEnv = (v: any) => String(v ?? "").trim().toLowerCase();
const parseBool = (v: any, fallback: boolean) => {
  const s = fromEnv(v);
  if (["1","true","yes","on","y"].includes(s)) return true;
  if (["0","false","no","off","n",""].includes(s)) return false;
  return fallback;
};

const isProd = process.env.NODE_ENV === 'production'
// 没配 HTTPS_ENABLED 就在 prod 下默认 true，dev 下默认 false
const httpsEnabled = parseBool(process.env.HTTPS_ENABLED, isProd)

const cookieOpts = {
  httpOnly: true,
  sameSite: httpsEnabled ? 'none' as const : 'lax' as const,
  secure: httpsEnabled,
  maxAge: 7 * 24 * 60 * 60 * 1000,
  domain: process.env.COOKIE_DOMAIN || undefined,
  path: '/'
}

// 导出 httpsEnabled 供其他模块使用
export { httpsEnabled }

export async function register(req: Request, res: Response) {
  try {
    const parsed = registerSchema.safeParse(req.body)
    if (!parsed.success) {
      return res.status(400).json({
        error: '参数不合法',
        details: parsed.error.errors
      })
    }
    const { username, password, name } = parsed.data

    const exists = db.prepare(`SELECT id FROM users WHERE username = ?`).get(username)
    if (exists) return res.status(409).json({ error: '用户名已注册' })

    const hash = await bcrypt.hash(password, 12)
    const result = db
      .prepare(`INSERT INTO users (username, password_hash, name) VALUES (?, ?, ?)`)
      .run(username, hash, name)

    if (!result.lastInsertRowid) {
      return res.status(500).json({ error: '注册失败' })
    }

    const token = jwt.sign({
      uid: Number(result.lastInsertRowid),
      username,
      name
    }, JWT_SECRET, { expiresIn: '7d' })
    
    res.cookie('token', token, cookieOpts)
    return res.json({
      user: {
        id: Number(result.lastInsertRowid),
        username,
        name
      }
    })
  } catch (error) {
    console.error('Registration error:', error)
    return res.status(500).json({ error: '服务器内部错误' })
  }
}

export async function login(req: Request, res: Response) {
  try {
    const parsed = loginSchema.safeParse(req.body)
    if (!parsed.success) {
      return res.status(400).json({
        error: '参数不合法',
        details: parsed.error.errors
      })
    }
    const { username, password } = parsed.data

    const user = db.prepare(`SELECT * FROM users WHERE username = ?`).get(username)
    if (!user || !isUser(user)) return res.status(401).json({ error: '用户名或密码错误' })

    const ok = await bcrypt.compare(password, user.password_hash)
    if (!ok) return res.status(401).json({ error: '用户名或密码错误' })

    const token = jwt.sign({
      uid: user.id,
      username: user.username,
      name: user.name
    }, JWT_SECRET, { expiresIn: '7d' })
    
    res.cookie('token', token, cookieOpts)
    return res.json({
      user: {
        id: user.id,
        username: user.username,
        name: user.name
      }
    })
  } catch (error) {
    console.error('Login error:', error)
    return res.status(500).json({ error: '服务器内部错误' })
  }
}

export function logout(_req: Request, res: Response) {
  res.clearCookie('token', { ...cookieOpts, maxAge: 0 })
  res.json({ ok: true })
}

export function authGuard(req: Request, res: Response, next: NextFunction) {
  const token = req.cookies?.token
  if (!token) return res.status(401).json({ error: '未登录' })
  
  try {
    const payload = jwt.verify(token, JWT_SECRET) as JWTPayload
    
    // 验证 payload 结构
    if (!payload.uid || !payload.username || !payload.name) {
      return res.status(401).json({ error: '无效的令牌' })
    }
    
    req.user = payload
    next()
  } catch (error) {
    console.error('Auth guard error:', error)
    return res.status(401).json({ error: '登录已过期' })
  }
}

export function me(req: Request, res: Response) {
  const token = req.cookies?.token
  if (!token) return res.status(200).json({ user: null })
  
  try {
    const payload = jwt.verify(token, JWT_SECRET) as JWTPayload
    
    // 验证 payload 结构
    if (!payload.uid || !payload.username || !payload.name) {
      return res.status(200).json({ user: null })
    }
    
    res.json({
      user: {
        id: payload.uid,
        username: payload.username,
        name: payload.name
      }
    })
  } catch (error) {
    console.error('Me endpoint error:', error)
    res.json({ user: null })
  }
}
