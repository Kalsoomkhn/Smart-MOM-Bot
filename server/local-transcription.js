import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { randomUUID } from 'node:crypto'
import { spawn } from 'node:child_process'
import ffmpegPath from 'ffmpeg-static'

const projectPath = (...parts) => path.resolve(process.cwd(), ...parts)

function configuredPath(value, fallback) {
  return path.resolve(value || fallback)
}

function run(command, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { windowsHide: true })
    let stdout = ''
    let stderr = ''
    child.stdout.on('data', (data) => { stdout += data })
    child.stderr.on('data', (data) => { stderr += data })
    child.on('error', reject)
    child.on('close', (code) => {
      if (code === 0) return resolve({ stdout, stderr })
      reject(new Error(`${path.basename(command)} exited with code ${code}: ${stderr.slice(-1500)}`))
    })
  })
}

export function speakerTurnsToTranscript(rawText) {
  const pieces = rawText
    .replace(/\r/g, '')
    .split(/(\[SPEAKER_TURN\])/g)
    .map((piece) => piece.trim())
    .filter(Boolean)

  let speaker = 1
  const segments = []
  for (const piece of pieces) {
    if (piece === '[SPEAKER_TURN]') {
      speaker = speaker === 1 ? 2 : 1
      continue
    }
    const text = piece.replace(/^\[[\d:.]+\s*-->\s*[\d:.]+\]\s*/gm, '').replace(/\s+/g, ' ').trim()
    if (text) segments.push({ speaker: `Speaker ${speaker}`, text })
  }

  return {
    text: segments.map((segment) => `${segment.speaker}: ${segment.text}`).join('\n'),
    segments
  }
}

export async function transcribeLocally(filePath) {
  const executable = configuredPath(
    process.env.WHISPER_CPP_PATH,
    process.platform === 'win32' ? projectPath('tools', 'whisper', 'whisper-cli.exe') : projectPath('tools', 'whisper', 'whisper-cli')
  )
  const model = configuredPath(process.env.WHISPER_MODEL_PATH, projectPath('models', 'ggml-small.en-tdrz.bin'))

  if (!fs.existsSync(executable) || !fs.existsSync(model)) {
    const error = new Error('Local transcription is not installed. Run scripts/setup-local-whisper.ps1, then restart the API.')
    error.code = 'LOCAL_TRANSCRIPTION_NOT_CONFIGURED'
    throw error
  }
  if (!ffmpegPath || !fs.existsSync(ffmpegPath)) throw new Error('The bundled FFmpeg executable is unavailable. Run npm install.')

  const jobId = randomUUID()
  const wavPath = path.join(os.tmpdir(), `smartmom-${jobId}.wav`)
  const outputBase = path.join(os.tmpdir(), `smartmom-${jobId}-transcript`)
  const outputText = `${outputBase}.txt`

  try {
    await run(ffmpegPath, ['-y', '-i', filePath, '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le', wavPath])
    await run(executable, ['-m', model, '-f', wavPath, '-tdrz', '-otxt', '-of', outputBase, '-l', process.env.WHISPER_LANGUAGE || 'en'])
    const parsed = speakerTurnsToTranscript(fs.readFileSync(outputText, 'utf8'))
    if (!parsed.text) throw new Error('The local Whisper model did not detect any speech in this recording.')
    return { ...parsed, mode: 'local-whisper' }
  } finally {
    fs.rmSync(wavPath, { force: true })
    fs.rmSync(outputText, { force: true })
  }
}
