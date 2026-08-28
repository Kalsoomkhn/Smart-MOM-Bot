import fs from 'node:fs'
import OpenAI from 'openai'
import { transcribeLocally } from '../local-transcription.js'

async function transcribeWithOpenAI(filePath) {
  if (!process.env.OPENAI_API_KEY) throw new Error('OPENAI_API_KEY is required when TRANSCRIPTION_PROVIDER=openai.')
  const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY })
  const result = await client.audio.transcriptions.create({
    file: fs.createReadStream(filePath),
    model: process.env.OPENAI_TRANSCRIPTION_MODEL || 'gpt-4o-transcribe-diarize',
    response_format: 'diarized_json',
    chunking_strategy: 'auto'
  })
  const segments = result.segments || []
  const text = segments.length
    ? segments.map((segment) => `${segment.speaker || 'Unknown Speaker'}: ${segment.text}`).join('\n')
    : result.text
  return { text, segments, mode: 'openai' }
}

export function transcribeWithSelectedProvider(filePath) {
  const provider = (process.env.TRANSCRIPTION_PROVIDER || 'local').toLowerCase()
  if (provider === 'local') return transcribeLocally(filePath)
  if (provider === 'openai') return transcribeWithOpenAI(filePath)
  throw new Error(`Unsupported transcription provider: ${provider}`)
}
