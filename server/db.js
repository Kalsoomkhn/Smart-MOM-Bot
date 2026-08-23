import pg from 'pg'
import { PGlite } from '@electric-sql/pglite'
import path from 'node:path'
import fs from 'node:fs'
import 'dotenv/config'

let clientPromise
async function client() {
  if (!clientPromise) {
    clientPromise = process.env.DATABASE_URL
      ? Promise.resolve(new pg.Pool({ connectionString: process.env.DATABASE_URL }))
      : (fs.mkdirSync(path.resolve('.data'), { recursive: true }), PGlite.create(path.resolve('.data', 'smartmom-postgres')))
  }
  return clientPromise
}

// Same query surface for managed PostgreSQL in production and persistent embedded
// PostgreSQL-compatible storage during local development.
export const pool = { query: async (...args) => (await client()).query(...args) }
export const databaseMode = process.env.DATABASE_URL ? 'postgresql' : 'embedded-pglite'

export async function migrate() {
  const statements = [
    `CREATE TABLE IF NOT EXISTS users (id uuid PRIMARY KEY, name text NOT NULL, email text UNIQUE NOT NULL, password_hash text NOT NULL, role text NOT NULL DEFAULT 'organizer', created_at timestamptz DEFAULT now())`,
    `ALTER TABLE users ADD COLUMN IF NOT EXISTS role text NOT NULL DEFAULT 'organizer'`,
    `CREATE TABLE IF NOT EXISTS meetings (id uuid PRIMARY KEY, owner_id uuid REFERENCES users(id) ON DELETE CASCADE, title text NOT NULL, status text NOT NULL DEFAULT 'uploaded', audio_path text, audio_mime text, transcript text DEFAULT '', summary jsonb, analysis jsonb, created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now())`,
    `CREATE TABLE IF NOT EXISTS meeting_members (meeting_id uuid REFERENCES meetings(id) ON DELETE CASCADE, user_id uuid REFERENCES users(id) ON DELETE CASCADE, access_role text NOT NULL DEFAULT 'participant', created_at timestamptz DEFAULT now(), PRIMARY KEY (meeting_id, user_id))`,
    `CREATE TABLE IF NOT EXISTS meeting_versions (id uuid PRIMARY KEY, meeting_id uuid REFERENCES meetings(id) ON DELETE CASCADE, editor_id uuid REFERENCES users(id), summary jsonb NOT NULL, created_at timestamptz DEFAULT now())`,
    `CREATE TABLE IF NOT EXISTS feedback (id uuid PRIMARY KEY, meeting_id uuid REFERENCES meetings(id) ON DELETE CASCADE, user_id uuid REFERENCES users(id), rating integer CHECK (rating BETWEEN 1 AND 5), comment text, created_at timestamptz DEFAULT now())`,
    `CREATE INDEX IF NOT EXISTS meetings_owner_idx ON meetings(owner_id, created_at DESC)`,
    `CREATE INDEX IF NOT EXISTS meeting_members_user_idx ON meeting_members(user_id, created_at DESC)`
  ]
  for (const statement of statements) await pool.query(statement)
}
