import fs from 'node:fs'
import OpenAI from 'openai'

const hasOpenAI = () => Boolean(process.env.OPENAI_API_KEY)
const client = () => new OpenAI({ apiKey: process.env.OPENAI_API_KEY })

function demoTranscript(title = 'Meeting') {
  const normalized = title.toLowerCase()
  if (normalized.includes('client') || normalized.includes('standup')) {
    return [
      'Speaker 1: This is the client requirements standup for SmartMOM Bot.',
      'Speaker 2: The team discussed meeting summaries, key decisions, action items, and participant feedback.',
      'Speaker 1: We agreed that the summary should be reviewed before it is saved or exported.',
      'Speaker 2: The organizer will verify upload, transcript review, feedback, and PDF export before the final demo.'
    ].join('\n')
  }
  if (normalized.includes('action')) {
    return [
      'Speaker 1: Kalsoom will prepare screenshots and the final demo script by Friday.',
      'Speaker 2: Usman will test audio upload, transcription, analysis, and PDF export today.',
      'Speaker 1: The remaining work is to make sure every button shows a clear success or error message.'
    ].join('\n')
  }
  return [
    'Speaker 1: Welcome to the FYP progress review for SmartMOM Bot.',
    'Speaker 2: Today we will confirm the requirements, review the user interface, and assign final presentation tasks.',
    'Speaker 1: The team needs to verify transcription, generated minutes, participant access, feedback, and PDF export.',
    'Speaker 2: Kalsoom will prepare the presentation while Usman completes the final testing checklist.'
  ].join('\n')
}

function demoAnalysis(transcript) {
  const lower = transcript.toLowerCase()
  if (lower.includes('client')) {
    return {
      agenda: ['Review client requirements', 'Confirm minutes structure', 'Prepare export-ready summary'],
      decisions: ['Review generated minutes before saving', 'Keep participant feedback in the workflow'],
      discussion: ['The team discussed how SmartMOM should present decisions, key points, action items, and feedback in a professional format.'],
      actions: [
        { owner: 'Demo Organizer', task: 'Verify upload, feedback, and PDF export', due: 'Before final demo' },
        { owner: 'Ayesha Participant', task: 'Review generated minutes and submit feedback', due: 'Today' }
      ],
      sentiment: {
        overall: 'positive',
        participants: [
          { name: 'Speaker 1', sentiment: 'Positive', engagement: 88 },
          { name: 'Speaker 2', sentiment: 'Neutral', engagement: 80 }
        ]
      }
    }
  }
  if (lower.includes('screenshots') || lower.includes('final demo script')) {
    return {
      agenda: ['Confirm remaining action items', 'Assign testing responsibilities'],
      decisions: ['Complete manual testing before presentation', 'Show clear user-facing messages for every important action'],
      discussion: ['The meeting focused on final preparation tasks and making the demo reliable for evaluation.'],
      actions: [
        { owner: 'Kalsoom', task: 'Prepare screenshots and final demo script', due: 'Friday' },
        { owner: 'Usman', task: 'Test upload, transcription, analysis, and export', due: 'Today' }
      ],
      sentiment: {
        overall: 'positive',
        participants: [
          { name: 'Speaker 1', sentiment: 'Positive', engagement: 86 },
          { name: 'Speaker 2', sentiment: 'Positive', engagement: 84 }
        ]
      }
    }
  }
  return {
    agenda: ['Review SmartMOM Bot requirements', 'Verify UI and workflow', 'Assign final presentation tasks'],
    decisions: ['Use SmartMOM for AI meeting minutes', 'Validate transcription, analysis, feedback, and PDF export before submission'],
    discussion: ['The team reviewed the FYP progress and identified the meeting-minutes workflow as the main demonstration path.'],
    actions: [
      { owner: 'Kalsoom', task: 'Prepare presentation and demo script', due: 'Next supervisor review' },
      { owner: 'Usman', task: 'Complete the final testing checklist', due: 'Before submission' }
    ],
    sentiment: {
      overall: 'positive',
      participants: [
        { name: 'Speaker 1', sentiment: 'Positive', engagement: 90 },
        { name: 'Speaker 2', sentiment: 'Neutral', engagement: 82 }
      ]
    }
  }
}

export async function transcribe(filePath, title) {
  if (!hasOpenAI()) {
    return { text: demoTranscript(title), segments: [], mode: 'demo' }
  }
  const result = await client().audio.transcriptions.create({
    file: fs.createReadStream(filePath),
    model: process.env.OPENAI_TRANSCRIPTION_MODEL || 'gpt-4o-transcribe-diarize',
    response_format: 'diarized_json',
    chunking_strategy: 'auto'
  })
  const segments = result.segments || []
  return { text: segments.length ? segments.map((s) => `${s.speaker || 'Unknown Speaker'}: ${s.text}`).join('\n') : result.text, segments, mode: 'openai' }
}

export async function analyze(transcript) {
  if (!hasOpenAI()) return { ...demoAnalysis(transcript), mode: 'demo' }
  const response = await client().responses.create({
    model: process.env.OPENAI_SUMMARY_MODEL || 'gpt-5-mini',
    input: `Analyze this meeting transcript. Return ONLY valid JSON with agenda:string[], decisions:string[], discussion:string[], actions:{owner:string,task:string,due:string}[], sentiment:{overall:'positive'|'neutral'|'negative',participants:{name:string,sentiment:string,engagement:number}[]}. Do not invent names, deadlines, or facts; use 'Unassigned'/'Not specified' when absent. Transcript:\n${transcript}`
  })
  const text = response.output_text.replace(/^```json\s*|\s*```$/g, '')
  return JSON.parse(text)
}
