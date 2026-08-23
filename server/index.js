import express from 'express'
import cors from 'cors'
import helmet from 'helmet'
import rateLimit from 'express-rate-limit'
import multer from 'multer'
import bcrypt from 'bcryptjs'
import fs from 'node:fs'
import path from 'node:path'
import { randomUUID } from 'node:crypto'
import PDFDocument from 'pdfkit'
import 'dotenv/config'
import { pool, migrate, databaseMode } from './db.js'
import { id, sign, requireAuth } from './auth.js'
import { transcribe, analyze } from './ai.js'

const app = express()
const uploadDir = path.resolve(process.env.UPLOAD_DIR || './uploads')
fs.mkdirSync(uploadDir, { recursive: true })

const upload = multer({
  storage: multer.diskStorage({
    destination: uploadDir,
    filename: (_, file, cb) => cb(null, `${randomUUID()}${path.extname(file.originalname)}`)
  }),
  limits: { fileSize: 200 * 1024 * 1024 },
  fileFilter: (_, file, cb) => cb(null, /^(audio\/(mpeg|wav|x-m4a|mp4|ogg|webm))$/.test(file.mimetype))
})

app.use(helmet())
app.use(cors({ origin: process.env.CLIENT_ORIGIN || 'http://localhost:5173' }))
app.use(express.json({ limit: '1mb' }))
app.use('/api', rateLimit({ windowMs: 15 * 60 * 1000, max: 300 }))
app.get('/health', (_req, res) => res.json({ status: 'ok', database: databaseMode }))

const asyncRoute = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next)
const publicUser = (user) => ({ id: user.id, name: user.name, email: user.email, role: user.role || 'organizer' })
const validRole = (role) => ['organizer', 'participant'].includes(role)

async function meetingFor(meetingId, userId) {
  const result = await pool.query(
    `SELECT m.id, m.owner_id, m.title, m.status, m.audio_path, m.audio_mime, m.transcript,
      m.summary, m.analysis, m.created_at, m.updated_at,
      CASE WHEN m.owner_id = $2 THEN 'organizer' ELSE mm.access_role END AS access_role
     FROM meetings m
     LEFT JOIN meeting_members mm ON mm.meeting_id = m.id AND mm.user_id = $2
     WHERE m.id = $1 AND (m.owner_id = $2 OR mm.user_id = $2)`,
    [meetingId, userId]
  )
  return result.rows[0]
}

async function organizerMeeting(meetingId, userId) {
  const meeting = await meetingFor(meetingId, userId)
  return meeting?.access_role === 'organizer' ? meeting : null
}

app.post('/api/auth/register', asyncRoute(async (req, res) => {
  const { name, email, password } = req.body
  const role = req.body.role || 'organizer'
  if (!name || !email || !password || password.length < 10) {
    return res.status(400).json({ error: 'Name, email, and a password of at least 10 characters are required.' })
  }
  if (!validRole(role)) return res.status(400).json({ error: 'Choose either Organizer or Participant.' })

  const user = {
    id: id(),
    name: name.trim(),
    email: email.toLowerCase().trim(),
    role,
    password_hash: await bcrypt.hash(password, 12)
  }
  await pool.query('INSERT INTO users(id,name,email,role,password_hash) VALUES($1,$2,$3,$4,$5)', [user.id, user.name, user.email, user.role, user.password_hash])
  res.status(201).json({ token: sign(user), user: publicUser(user) })
}))

app.post('/api/auth/login', asyncRoute(async (req, res) => {
  const result = await pool.query('SELECT * FROM users WHERE email=$1', [req.body.email?.toLowerCase().trim()])
  const user = result.rows[0]
  if (!user || !await bcrypt.compare(req.body.password || '', user.password_hash)) {
    return res.status(401).json({ error: 'Invalid email or password.' })
  }
  res.json({ token: sign(user), user: publicUser(user) })
}))

app.get('/api/auth/me', requireAuth, asyncRoute(async (req, res) => {
  const result = await pool.query('SELECT id,name,email,role FROM users WHERE id=$1', [req.user.sub])
  if (!result.rows[0]) return res.sendStatus(404)
  res.json(publicUser(result.rows[0]))
}))

app.get('/api/meetings', requireAuth, asyncRoute(async (req, res) => {
  const result = await pool.query(
    `SELECT DISTINCT m.id, m.title, m.status, m.transcript, m.summary, m.analysis,
      m.created_at, m.updated_at,
      CASE WHEN m.owner_id = $1 THEN 'organizer' ELSE COALESCE(mm.access_role, 'participant') END AS access_role
     FROM meetings m
     LEFT JOIN meeting_members mm ON mm.meeting_id = m.id
     WHERE m.owner_id = $1 OR mm.user_id = $1
     ORDER BY m.created_at DESC`,
    [req.user.sub]
  )
  res.json(result.rows)
}))

app.post('/api/meetings', requireAuth, upload.single('audio'), asyncRoute(async (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'A supported audio file is required.' })
  const meeting = {
    id: id(),
    owner: req.user.sub,
    title: req.body.title?.slice(0, 150) || path.parse(req.file.originalname).name,
    path: req.file.path,
    mime: req.file.mimetype
  }
  await pool.query(
    'INSERT INTO meetings(id,owner_id,title,status,audio_path,audio_mime) VALUES($1,$2,$3,$4,$5,$6)',
    [meeting.id, meeting.owner, meeting.title, 'uploaded', meeting.path, meeting.mime]
  )
  await pool.query(
    'INSERT INTO meeting_members(meeting_id,user_id,access_role) VALUES($1,$2,$3) ON CONFLICT (meeting_id,user_id) DO NOTHING',
    [meeting.id, meeting.owner, 'organizer']
  )
  res.status(201).json({ id: meeting.id, title: meeting.title, status: 'uploaded', access_role: 'organizer' })
}))

app.get('/api/meetings/:id/participants', requireAuth, asyncRoute(async (req, res) => {
  const meeting = await meetingFor(req.params.id, req.user.sub)
  if (!meeting) return res.sendStatus(404)
  const result = await pool.query(
    `SELECT u.id, u.name, u.email, u.role, mm.access_role
     FROM meeting_members mm
     JOIN users u ON u.id = mm.user_id
     WHERE mm.meeting_id = $1
     ORDER BY mm.created_at ASC`,
    [meeting.id]
  )
  res.json(result.rows)
}))

app.post('/api/meetings/:id/participants', requireAuth, asyncRoute(async (req, res) => {
  const meeting = await organizerMeeting(req.params.id, req.user.sub)
  if (!meeting) return res.sendStatus(404)
  const emails = Array.isArray(req.body.emails) ? req.body.emails : String(req.body.email || '').split(',')
  const normalized = [...new Set(emails.map((email) => email.toLowerCase().trim()).filter(Boolean))].slice(0, 20)
  if (!normalized.length) return res.status(400).json({ error: 'At least one registered participant email is required.' })

  const invited = []
  const missing = []
  for (const email of normalized) {
    const result = await pool.query('SELECT id,name,email,role FROM users WHERE email=$1', [email])
    const user = result.rows[0]
    if (!user) {
      missing.push(email)
      continue
    }
    await pool.query(
      'INSERT INTO meeting_members(meeting_id,user_id,access_role) VALUES($1,$2,$3) ON CONFLICT (meeting_id,user_id) DO UPDATE SET access_role=EXCLUDED.access_role',
      [meeting.id, user.id, user.id === meeting.owner_id ? 'organizer' : 'participant']
    )
    invited.push(publicUser(user))
  }
  res.status(201).json({ invited, missing })
}))

app.post('/api/meetings/:id/transcribe', requireAuth, asyncRoute(async (req, res) => {
  const meeting = await organizerMeeting(req.params.id, req.user.sub)
  if (!meeting) return res.sendStatus(404)
  await pool.query("UPDATE meetings SET status='transcribing' WHERE id=$1", [meeting.id])
  try {
    const result = await transcribe(meeting.audio_path)
    await pool.query("UPDATE meetings SET transcript=$1,status='transcribed',updated_at=now() WHERE id=$2", [result.text, meeting.id])
    res.json(result)
  } catch (error) {
    await pool.query("UPDATE meetings SET status='failed' WHERE id=$1", [meeting.id])
    throw error
  }
}))

app.put('/api/meetings/:id/transcript', requireAuth, asyncRoute(async (req, res) => {
  const meeting = await organizerMeeting(req.params.id, req.user.sub)
  if (!meeting) return res.sendStatus(404)
  if (typeof req.body.transcript !== 'string' || !req.body.transcript.trim()) return res.status(400).json({ error: 'Transcript is required.' })
  await pool.query("UPDATE meetings SET transcript=$1,status='transcribed',updated_at=now() WHERE id=$2", [req.body.transcript, meeting.id])
  res.sendStatus(204)
}))

app.post('/api/meetings/:id/analyze', requireAuth, asyncRoute(async (req, res) => {
  const meeting = await organizerMeeting(req.params.id, req.user.sub)
  if (!meeting) return res.sendStatus(404)
  if (!meeting.transcript.trim()) return res.status(400).json({ error: 'Transcribe or enter a transcript first.' })
  const result = await analyze(meeting.transcript)
  const summary = { agenda: result.agenda || [], decisions: result.decisions || [], discussion: result.discussion || [], actions: result.actions || [] }
  await pool.query("UPDATE meetings SET summary=$1,analysis=$2,status='ready',updated_at=now() WHERE id=$3", [summary, result.sentiment || {}, meeting.id])
  res.json({ summary, analysis: result.sentiment || {} })
}))

app.put('/api/meetings/:id/summary', requireAuth, asyncRoute(async (req, res) => {
  const meeting = await organizerMeeting(req.params.id, req.user.sub)
  if (!meeting) return res.sendStatus(404)
  const summary = req.body.summary
  if (!summary || !Array.isArray(summary.agenda) || !Array.isArray(summary.decisions) || !Array.isArray(summary.actions)) return res.status(400).json({ error: 'Invalid summary.' })
  await pool.query("UPDATE meetings SET summary=$1,status='saved',updated_at=now() WHERE id=$2", [summary, meeting.id])
  await pool.query('INSERT INTO meeting_versions(id,meeting_id,editor_id,summary) VALUES($1,$2,$3,$4)', [id(), meeting.id, req.user.sub, summary])
  res.json({ summary })
}))

app.delete('/api/meetings/:id', requireAuth, asyncRoute(async (req, res) => {
  const meeting = await organizerMeeting(req.params.id, req.user.sub)
  if (!meeting) return res.sendStatus(404)
  if (meeting.audio_path) fs.rm(meeting.audio_path, { force: true }, () => {})
  await pool.query('DELETE FROM meetings WHERE id=$1', [meeting.id])
  res.sendStatus(204)
}))

app.post('/api/meetings/:id/feedback', requireAuth, asyncRoute(async (req, res) => {
  const meeting = await meetingFor(req.params.id, req.user.sub)
  if (!meeting) return res.sendStatus(404)
  const { rating, comment = '' } = req.body
  if (!Number.isInteger(rating) || rating < 1 || rating > 5) return res.status(400).json({ error: 'A rating from 1 to 5 is required.' })
  await pool.query('INSERT INTO feedback(id,meeting_id,user_id,rating,comment) VALUES($1,$2,$3,$4,$5)', [id(), meeting.id, req.user.sub, rating, comment.slice(0, 2000)])
  res.status(201).json({ ok: true })
}))

app.get('/api/meetings/:id/export.pdf', requireAuth, asyncRoute(async (req, res) => {
  const meeting = await meetingFor(req.params.id, req.user.sub)
  if (!meeting) return res.sendStatus(404)
  const summary = meeting.summary || {}
  res.setHeader('Content-Type', 'application/pdf')
  res.setHeader('Content-Disposition', `attachment; filename="${meeting.title.replace(/[^a-z0-9]/gi, '-')}-minutes.pdf"`)
  const doc = new PDFDocument({ margin: 50 })
  doc.pipe(res)
  doc.fontSize(22).text(meeting.title)
  doc.fontSize(10).fillColor('#555').text(`Generated ${new Date().toLocaleString()}`)
  for (const [title, items] of [['Agenda', summary.agenda], ['Key decisions', summary.decisions], ['Discussion points', summary.discussion]]) {
    doc.moveDown().fillColor('#111').fontSize(15).text(title)
    doc.fontSize(11)
    ;(items || []).forEach((item) => doc.text(`- ${item}`))
  }
  doc.moveDown().fontSize(15).text('Action items')
  doc.fontSize(11)
  ;(summary.actions || []).forEach((action) => doc.text(`- ${action.owner || 'Unassigned'}: ${action.task} (${action.due || 'Not specified'})`))
  doc.end()
}))

app.use((err, req, res, _next) => {
  console.error(err)
  res.status(err.code === 'LIMIT_FILE_SIZE' ? 413 : 500).json({ error: err.message || 'Unexpected server error.' })
})

migrate()
  .then(() => app.listen(process.env.PORT || 3001, () => console.log(`API listening with ${databaseMode}`)))
  .catch((error) => {
    console.error('Database migration failed', error)
    process.exit(1)
  })
