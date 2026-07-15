import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = join(__dirname, '..')

const apiConfig = readFileSync(join(root, 'src/config/api.js'), 'utf8')
const nginxConfig = readFileSync(join(root, 'nginx.conf'), 'utf8')
const viteConfig = readFileSync(join(root, 'vite.config.js'), 'utf8')
const aiChatView = readFileSync(join(root, 'src/views/AIChat.vue'), 'utf8')

const legacyApiPrefixes = ['/chat/', '/knowledge/', '/note/', '/review/', '/user/', '/file/']

for (const prefix of legacyApiPrefixes) {
  assert(
    !apiConfig.includes(`: '${prefix}`) && !apiConfig.includes(`=> \`${prefix}`),
    `API endpoint should use /api prefix instead of ${prefix}`,
  )
}

assert(
  apiConfig.includes("agentQueryStream: '/api/chat/agent/query/stream'"),
  'AI chat stream endpoint should use /api/chat/agent/query/stream',
)

assert(
  aiChatView.includes('apiConfig.endpoints.agentQueryStream'),
  'AIChat.vue should use the centralized /api-prefixed endpoint',
)

for (const blockedLocation of ['location /chat/', 'location /knowledge/', 'location /note/', 'location /review/', 'location /user/', 'location /file/']) {
  assert(!nginxConfig.includes(blockedLocation), `nginx should not directly proxy page-conflicting route ${blockedLocation}`)
}

for (const requiredLocation of ['location /api/chat/', 'location /api/knowledge/', 'location /api/note/', 'location /api/review/', 'location /api/user/', 'location /api/file/']) {
  assert(nginxConfig.includes(requiredLocation), `nginx should proxy ${requiredLocation}`)
}

assert(!viteConfig.includes("'/chat/") && !viteConfig.includes("'/knowledge/"), 'Vite proxy should avoid non-/api backend route prefixes')
assert(viteConfig.includes("'/api/chat'"), 'Vite should proxy /api/chat to backend')
assert(viteConfig.includes("'/api/user'"), 'Vite should proxy /api/user to user service')
