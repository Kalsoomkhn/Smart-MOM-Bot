import { sharedPipeline } from './model-runtime.js'

const DEFAULT_MODEL = 'Xenova/distilbert-base-uncased-finetuned-sst-2-english'

function speakerText(transcript) {
  const speakers = new Map()
  for (const line of transcript.split(/\r?\n/)) {
    const match = line.match(/^([^:]{1,80}):\s*(.+)$/)
    const name = match?.[1]?.trim() || 'All participants'
    const text = match?.[2]?.trim() || line.trim()
    if (text) speakers.set(name, `${speakers.get(name) || ''} ${text}`.trim())
  }
  return [...speakers.entries()]
}

export async function analyzeSentiment(transcript) {
  const model = process.env.LOCAL_SENTIMENT_MODEL || DEFAULT_MODEL
  const classifier = await sharedPipeline('sentiment-analysis', model, { dtype: process.env.LOCAL_MODEL_DTYPE || 'q4' })
  const entries = speakerText(transcript)
  const totalWords = entries.reduce((sum, [, text]) => sum + text.split(/\s+/).length, 0) || 1
  const participants = []
  let signedScore = 0
  for (const [name, text] of entries) {
    const [result] = await classifier(text.slice(0, 4000), { truncation: true })
    const positive = String(result.label).toUpperCase().includes('POSITIVE')
    const score = Number(result.score || 0)
    signedScore += positive ? score : -score
    participants.push({
      name,
      sentiment: positive ? 'Positive' : 'Negative',
      engagement: Math.round((text.split(/\s+/).length / totalWords) * 100)
    })
  }
  const average = signedScore / Math.max(entries.length, 1)
  return {
    overall: average > 0.2 ? 'positive' : average < -0.2 ? 'negative' : 'neutral',
    participants,
    model,
    engagementMethod: 'share-of-spoken-words'
  }
}
