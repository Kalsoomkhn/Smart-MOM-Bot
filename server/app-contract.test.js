import { describe, expect, it } from 'vitest'
import fs from 'node:fs'

const serverSource = fs.readFileSync(new URL('./index.js', import.meta.url), 'utf8')

describe('server application contract', () => {
  it('keeps the built-in demo accounts available for evaluation', () => {
    expect(serverSource).toContain('admin@smartmom.test')
    expect(serverSource).toContain('Admin@12345')
    expect(serverSource).toContain('participant@smartmom.test')
    expect(serverSource).toContain('Participant@12345')
  })

  it('seeds realistic demo meetings and feedback', () => {
    expect(serverSource).toContain('FYP Progress Review')
    expect(serverSource).toContain('Client Requirements Standup')
    expect(serverSource).toContain('Transcript Review Queue Sample')
    expect(serverSource).toContain('Clear action items and decisions')
  })

  it('returns clear validation errors for common failure paths', () => {
    expect(serverSource).toContain('This email is already registered')
    expect(serverSource).toContain('No source audio is available for this meeting')
    expect(serverSource).toContain('Audio files must be below 200 MB')
    expect(serverSource).toContain('AI processing is not configured')
  })
})
