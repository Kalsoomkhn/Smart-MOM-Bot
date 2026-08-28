import { transcribeWithSelectedProvider } from './ai/transcription-service.js'
import { generateMinutes } from './ai/minutes-service.js'
import { analyzeSentiment } from './ai/sentiment-service.js'

// Routes depend on this stable facade; model providers remain independently replaceable.
export const transcribe = transcribeWithSelectedProvider

export async function analyze(transcript) {
  const [minutes, sentiment] = await Promise.all([
    generateMinutes(transcript),
    analyzeSentiment(transcript)
  ])
  return { ...minutes, sentiment, mode: minutes.mode }
}
