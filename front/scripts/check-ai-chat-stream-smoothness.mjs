import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const source = readFileSync(join(__dirname, '..', 'src/views/AIChat.vue'), 'utf8')

assert(
  !source.includes('for (const char of remainingContent)'),
  'AIChat.vue still updates assistant output one character at a time',
)

assert(
  !source.includes('watch(messages, () => {'),
  'AIChat.vue still deep-watches messages and scrolls on every mutation',
)

assert(
  source.includes('scheduleScrollToBottom'),
  'AIChat.vue should schedule scroll updates instead of forcing them inline',
)

assert(
  source.includes('renderedContent'),
  'AIChat.vue should cache rendered assistant HTML instead of parsing Markdown on every chunk',
)
