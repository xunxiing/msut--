import { db } from './db.js';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { z } from 'zod';
const registerSchema = z.object({
    email: z.string().email(),
    password: z.string().min(6).max(72),
    name: z.string().min(1).max(32)
});
const loginSchema = z.object({
    email: z.string().email(),
    password: z.string().min(6).max(72)
});
const JWT_SECRET = process.env.JWT_SECRET || 'dev';
const isProd = process.env.NODE_ENV === 'production';
const cookieOpts = {
    httpOnly: true,
    sameSite: 'lax',
    secure: isProd,
    maxAge: 7 * 24 * 60 * 60 * 1000
};
export async function register(req, res) {
    const parsed = registerSchema.safeParse(req.body);
    if (!parsed.success)
        return res.status(400).json({ error: '参数不合法' });
    const { email, password, name } = parsed.data;
    const exists = db.prepare(`SELECT id FROM users WHERE email = ?`).get(email);
    if (exists)
        return res.status(409).json({ error: '邮箱已注册' });
    const hash = await bcrypt.hash(password, 12);
    const result = db
        .prepare(`INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)`)
        .run(email, hash, name);
    const token = jwt.sign({ uid: result.lastInsertRowid, email, name }, JWT_SECRET, { expiresIn: '7d' });
    res.cookie('token', token, cookieOpts);
    return res.json({ id: result.lastInsertRowid, email, name });
}
export async function login(req, res) {
    const parsed = loginSchema.safeParse(req.body);
    if (!parsed.success)
        return res.status(400).json({ error: '参数不合法' });
    const { email, password } = parsed.data;
    const user = db.prepare(`SELECT * FROM users WHERE email = ?`).get(email);
    if (!user)
        return res.status(401).json({ error: '邮箱或密码错误' });
    const ok = await bcrypt.compare(password, user.password_hash);
    if (!ok)
        return res.status(401).json({ error: '邮箱或密码错误' });
    const token = jwt.sign({ uid: user.id, email: user.email, name: user.name }, JWT_SECRET, { expiresIn: '7d' });
    res.cookie('token', token, cookieOpts);
    return res.json({ id: user.id, email: user.email, name: user.name });
}
export function logout(_req, res) {
    res.clearCookie('token', { ...cookieOpts, maxAge: 0 });
    res.json({ ok: true });
}
export function authGuard(req, res, next) {
    const token = req.cookies?.token;
    if (!token)
        return res.status(401).json({ error: '未登录' });
    try {
        const payload = jwt.verify(token, JWT_SECRET);
        req.user = payload;
        next();
    }
    catch {
        return res.status(401).json({ error: '登录已过期' });
    }
}
export function me(req, res) {
    const token = req.cookies?.token;
    if (!token)
        return res.status(200).json({ user: null });
    try {
        const payload = jwt.verify(token, JWT_SECRET);
        res.json({ user: { id: payload.uid, email: payload.email, name: payload.name } });
    }
    catch {
        res.json({ user: null });
    }
}
//# sourceMappingURL=auth.js.map