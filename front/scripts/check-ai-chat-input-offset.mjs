import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const source = readFileSync(join(__dirname, '..', 'src/views/AIChat.vue'), 'utf8')

assert(
  source.includes('padding: 16px 12px 20px;'),
  'AIChat.vue should leave extra bottom padding in the messages container',
)

assert(
  source.includes('padding: 8px 12px 18px;'),
  'AIChat.vue should lift the chat input with extra bottom padding',
)
