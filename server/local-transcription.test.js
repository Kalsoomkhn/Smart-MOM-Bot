import { describe, expect, it } from 'vitest'
import { speakerTurnsToTranscript } from './local-transcription.js'

describe('local Whisper speaker-turn parsing', () => {
  it('turns tinydiarize markers into readable speaker labels', () => {
    const result = speakerTurnsToTranscript(`
[00:00:00.000 --> 00:00:02.000] Hello everyone. [SPEAKER_TURN]
[00:00:02.000 --> 00:00:04.000] Welcome to the meeting. [SPEAKER_TURN]
[00:00:04.000 --> 00:00:06.000] Let us begin.
`)
    expect(result.text).toBe('Speaker 1: Hello everyone.\nSpeaker 2: Welcome to the meeting.\nSpeaker 1: Let us begin.')
    expect(result.segments).toHaveLength(3)
  })
})
