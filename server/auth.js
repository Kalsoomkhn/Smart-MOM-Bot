import jwt from 'jsonwebtoken'
import { randomUUID, randomBytes } from 'node:crypto'
export const id = () => randomUUID()
const secret = process.env.JWT_SECRET || randomBytes(48).toString('hex')
if (!process.env.JWT_SECRET) console.warn('Using an ephemeral development JWT secret. Set JWT_SECRET before production deployment.')
export function sign(user) { return jwt.sign({ sub: user.id, email: user.email }, secret, { expiresIn: '8h' }) }
export function requireAuth(req, res, next) { try { const token = req.headers.authorization?.replace('Bearer ', ''); if (!token) throw Error(); req.user = jwt.verify(token, secret); next() } catch { res.status(401).json({ error: 'Authentication required.' }) } }
