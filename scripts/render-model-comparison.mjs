import fs from 'node:fs'
import path from 'node:path'
import { marked } from 'marked'

const source = path.resolve('docs/AI_Model_Comparison.md')
const destination = path.resolve('docs/AI_Model_Comparison.html')
const markdown = fs.readFileSync(source, 'utf8')
const content = marked.parse(markdown, { gfm: true })

const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>SmartMOM Bot — AI Model Comparison</title>
<style>
  @page { size: A4; margin: 2cm; }
  body { font-family: Calibri, Arial, sans-serif; color: #172033; font-size: 10.5pt; line-height: 1.35; }
  h1 { color: #17365d; font-size: 24pt; border-bottom: 2px solid #4f81bd; padding-bottom: 8px; }
  h2 { color: #1f4e79; font-size: 16pt; margin-top: 22px; }
  h3 { color: #2f5597; font-size: 13pt; margin-top: 16px; }
  table { border-collapse: collapse; width: 100%; margin: 10px 0 16px; font-size: 8.5pt; }
  th { background: #1f4e79; color: white; font-weight: bold; }
  th, td { border: 1px solid #9eacc0; padding: 6px; vertical-align: top; }
  tr:nth-child(even) td { background: #eef3f8; }
  code { font-family: Consolas, monospace; background: #eef1f5; padding: 1px 3px; }
  a { color: #0563c1; }
  blockquote { border-left: 4px solid #4f81bd; padding-left: 10px; color: #44546a; }
</style>
</head>
<body>${content}</body>
</html>`

fs.writeFileSync(destination, html)
console.log(destination)
