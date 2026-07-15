import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const projectRoot = join(__dirname, '..')

const filesToCheck = [
  'src/composables/useAuthImage.js',
  'src/store/session.js',
  'src/store/user.js',
  'src/views/KnowledgeBase.vue',
  'src/views/AIChat.vue',
  'src/views/Sessions.vue',
  'src/views/DailyReview.vue',
  'src/views/NoteEditor.vue',
  'src/views/Profile.vue',
  'src/views/My.vue',
  'src/components/RelatedNotes.vue',
  'src/components/InlineCompletion.vue',
]

for (const relativePath of filesToCheck) {
  const source = readFileSync(join(projectRoot, relativePath), 'utf8')
  assert(!source.includes('userStore.token'), `${relativePath} still reads userStore.token`)
  assert(
    !source.includes("localStorage.getItem('jwt_token')"),
    `${relativePath} still reads jwt_token directly`,
  )
  assert(!source.includes('Authorization: `Bearer'), `${relativePath} still builds Authorization manually`)
  assert(!source.includes("'Authorization': `Bearer"), `${relativePath} still builds Authorization manually`)
}

const knowledgeBaseSource = readFileSync(join(projectRoot, 'src/views/KnowledgeBase.vue'), 'utf8')
for (const staleSymbol of ['van-action-sheet', 'showActions', 'documentActions', 'onActionSelect']) {
  assert(!knowledgeBaseSource.includes(staleSymbol), `KnowledgeBase.vue still contains ${staleSymbol}`)
}

const storage = new Map()
globalThis.localStorage = {
  getItem: (key) => storage.get(key) ?? null,
  setItem: (key, value) => storage.set(key, String(value)),
  removeItem: (key) => storage.delete(key),
}

const { getAuthHeaders, getLoginRedirect, setAuthToken, clearAuthToken } = await import('../src/utils/auth.js')

clearAuthToken()
assert.deepEqual(getAuthHeaders({ Accept: 'application/json' }), { Accept: 'application/json' })

setAuthToken('token-123')
assert.deepEqual(getAuthHeaders({ Accept: 'application/json' }), {
  Accept: 'application/json',
  Authorization: 'Bearer token-123',
})
assert.deepEqual(getLoginRedirect('/notes/abc'), {
  path: '/login',
  query: { redirect: '/notes/abc' },
})

clearAuthToken()
