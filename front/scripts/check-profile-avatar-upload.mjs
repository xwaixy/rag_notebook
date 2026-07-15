import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const projectRoot = join(__dirname, '..')
const repoRoot = join(projectRoot, '..')
const source = readFileSync(join(projectRoot, 'src/views/Profile.vue'), 'utf8')
const uploadViewSource = readFileSync(join(repoRoot, 'DjangoUserService/apps/file/views.py'), 'utf8')
const uploadSerializerSource = readFileSync(join(repoRoot, 'DjangoUserService/apps/file/serializers.py'), 'utf8')

const uploadCallMatch = source.match(/axios\.post\(`\$\{apiConfig\.userBaseURL\}\$\{apiConfig\.endpoints\.uploadFile\}`,[\s\S]*?\n\s*\}\);/)
assert(uploadCallMatch, 'Profile.vue avatar upload axios.post call was not found')

const uploadCall = uploadCallMatch[0]

assert(
  !uploadCall.includes("'Content-Type': 'multipart/form-data'"),
  'Avatar upload must not set multipart/form-data manually; axios needs to add the boundary',
)

assert(
  uploadCall.includes('timeout:'),
  'Avatar upload request should have a timeout so the loading toast cannot hang forever',
)

assert(
  source.includes('finally') && source.includes('loadingInstance.close()'),
  'Avatar upload loading toast should be closed from a finally block',
)

assert(
  source.includes('MAX_AVATAR_SIZE') && source.includes('2 * 1024 * 1024'),
  'Avatar upload should validate the 2MB backend size limit before sending the request',
)

assert(
  source.includes('图片大小不能超过2MB'),
  'Avatar upload should show the 2MB size limit in the frontend validation message',
)

assert(
  uploadSerializerSource.includes('2 * 1024 * 1024') && uploadSerializerSource.includes('图片大小不能超过2MB'),
  'Django avatar upload serializer should enforce the same 2MB size limit',
)

assert(
  source.includes('ALLOWED_AVATAR_TYPES') && source.includes('image/jpeg') && source.includes('image/png') && source.includes('image/gif'),
  'Avatar upload should validate the backend-supported image formats before sending the request',
)

assert(
  source.includes('getAvatarUploadErrorMessage') && source.includes('error.response?.data'),
  'Avatar upload should show the specific backend error message instead of a generic failure',
)

assert(
  source.includes('onChange:') && source.includes('.jpg,.jpeg,.png,.gif'),
  'Avatar file picker should only suggest backend-supported image extensions',
)

assert(
  uploadViewSource.includes('mkdir(parents=True, exist_ok=True)'),
  'Django avatar upload should create MEDIA_ROOT/img before writing the uploaded file',
)
