import path from 'node:path'
import { env, pipeline } from '@huggingface/transformers'

env.cacheDir = path.resolve(process.env.HF_MODEL_CACHE || './models/huggingface')
env.allowLocalModels = true

const pipelines = new Map()

export function sharedPipeline(task, model, options = {}) {
  const key = `${task}:${model}:${JSON.stringify(options)}`
  if (!pipelines.has(key)) pipelines.set(key, pipeline(task, model, options))
  return pipelines.get(key)
}
