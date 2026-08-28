import OpenAI from 'openai'
import { sharedPipeline } from './model-runtime.js'

const DEFAULT_MODEL = 'onnx-community/Qwen2.5-1.5B-Instruct'

function cleanJson(text) {
  const cleaned = text.replace(/```(?:json)?/gi, '').replace(/```/g, '').trim()
  const start = cleaned.indexOf('{')
  const end = cleaned.lastIndexOf('}')
  if (start < 0 || end < start) throw new Error('The local minutes model did not return a JSON object.')
  return JSON.parse(cleaned.slice(start, end + 1))
}

const strings = (value) => Array.isArray(value)
  ? value.filter((item) => typeof item === 'string').map((item) => item.trim()).filter(Boolean)
  : []

export function normalizeMinutes(value) {
  const actions = Array.isArray(value?.actions) ? value.actions.map((action) => ({
    owner: String(action?.owner || 'Unassigned'),
    task: String(action?.task || '').trim(),
    due: String(action?.due || 'Not specified')
  })).filter((action) => action.task) : []
  return {
    agenda: strings(value?.agenda),
    decisions: strings(value?.decisions),
    discussion: strings(value?.discussion),
    actions
  }
}

export function reconcileActions(minutes, transcript) {
  const explicit = [...transcript.matchAll(/\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:will|shall|must|is going to)\s+([^.!?\n]+)/g)]
    .map((match) => ({ owner: match[1], words: match[2].toLowerCase().split(/\W+/).filter((word) => word.length > 3) }))
  const actions = minutes.actions.map((action) => {
    const taskWords = action.task.toLowerCase().split(/\W+/).filter((word) => word.length > 3)
    const evidence = explicit.find((candidate) => taskWords.some((word) => candidate.words.includes(word)))
    return evidence ? { ...action, owner: evidence.owner } : action
  })
  const discussion = minutes.discussion.filter((item) => !/^no (specific |further )?discussion\.?$/i.test(item))
  return { ...minutes, discussion, actions }
}

async function localMinutes(transcript) {
  const model = process.env.LOCAL_MINUTES_MODEL || DEFAULT_MODEL
  const generator = await sharedPipeline('text-generation', model, { dtype: process.env.LOCAL_MODEL_DTYPE || 'q4' })
  const messages = [
    { role: 'system', content: 'You extract faithful meeting minutes. Output JSON only. Never invent facts, people, decisions, or dates. For an action such as "Ali will run tests by Thursday", owner is "Ali", task is "Run tests", and due is "Thursday". Do not turn decisions into actions or write filler such as "no discussion".' },
    { role: 'user', content: `Extract this transcript into exactly these JSON keys: {"agenda":string[],"decisions":string[],"discussion":string[],"actions":[{"owner":string,"task":string,"due":string}]}. Copy an explicitly named action owner even when a different speaker says the sentence. Use "Unassigned" and "Not specified" only when absent. Use [] when a category has no evidence. Transcript:\n${transcript}` }
  ]
  const output = await generator(messages, {
    max_new_tokens: Number(process.env.LOCAL_MINUTES_MAX_TOKENS || 700),
    do_sample: false,
    repetition_penalty: 1.08
  })
  const generated = output[0]?.generated_text
  const text = Array.isArray(generated) ? generated.at(-1)?.content : generated
  return { ...reconcileActions(normalizeMinutes(cleanJson(String(text || ''))), transcript), mode: 'local-qwen' }
}

async function openAiMinutes(transcript) {
  if (!process.env.OPENAI_API_KEY) throw new Error('OPENAI_API_KEY is required when MINUTES_PROVIDER=openai.')
  const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY })
  const response = await client.responses.create({
    model: process.env.OPENAI_SUMMARY_MODEL || 'gpt-5-mini',
    input: `Return only JSON with agenda:string[], decisions:string[], discussion:string[], actions:{owner:string,task:string,due:string}[]. Do not invent facts. Transcript:\n${transcript}`
  })
  return { ...normalizeMinutes(cleanJson(response.output_text)), mode: 'openai' }
}

export function generateMinutes(transcript) {
  const provider = (process.env.MINUTES_PROVIDER || 'local').toLowerCase()
  if (provider === 'local') return localMinutes(transcript)
  if (provider === 'openai') return openAiMinutes(transcript)
  throw new Error(`Unsupported minutes provider: ${provider}`)
}
