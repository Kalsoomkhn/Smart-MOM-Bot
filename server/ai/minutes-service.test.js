import { describe, expect, it } from 'vitest'
import { normalizeMinutes, reconcileActions } from './minutes-service.js'

describe('minutes provider output boundary', () => {
  it('normalizes model output without leaking unexpected fields', () => {
    expect(normalizeMinutes({
      agenda: [' Review progress '],
      decisions: ['Ship Friday'],
      discussion: ['Testing was discussed'],
      actions: [{ owner: '', task: 'Run tests', due: '' }],
      sentiment: { overall: 'invented' }
    })).toEqual({
      agenda: ['Review progress'],
      decisions: ['Ship Friday'],
      discussion: ['Testing was discussed'],
      actions: [{ owner: 'Unassigned', task: 'Run tests', due: 'Not specified' }]
    })
  })

  it('grounds explicit action owners in transcript evidence', () => {
    const minutes = { agenda: [], decisions: [], discussion: ['No specific discussion'], actions: [{ owner: 'Speaker 1', task: 'Run tests', due: 'Thursday' }] }
    expect(reconcileActions(minutes, 'Speaker 1: Ali will run tests by Thursday.')).toEqual({
      agenda: [], decisions: [], discussion: [], actions: [{ owner: 'Ali', task: 'Run tests', due: 'Thursday' }]
    })
  })
})
