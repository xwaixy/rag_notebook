import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = join(__dirname, '..', '..')

const devCompose = readFileSync(join(root, 'docker-compose.dev.yml'), 'utf8')
const devDockerfilePath = join(root, 'front/Dockerfile.dev')

assert(
  existsSync(devDockerfilePath),
  'front development mode should define front/Dockerfile.dev so it does not reuse the production nginx image',
)

const devDockerfile = readFileSync(devDockerfilePath, 'utf8')

assert(
  devDockerfile.includes('FROM node:22-alpine'),
  'front/Dockerfile.dev should be based on node:22-alpine so npm is available',
)

assert(
  devDockerfile.includes('npm --version'),
  'front/Dockerfile.dev should verify npm during image build instead of failing later at runtime',
)

assert(
  devCompose.includes('dockerfile: Dockerfile.dev'),
  'docker-compose.dev.yml front service should build with Dockerfile.dev',
)

assert(
  !devCompose.includes('build: null'),
  'docker-compose.dev.yml should not rely on build: null because it can still leave the production build active after compose merge',
)

assert(
  devCompose.includes('npm run dev -- --host 0.0.0.0 --port 80'),
  'front development mode should start Vite dev server on container port 80',
)

assert(
  devCompose.includes('PATH: "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"'),
  'front development mode should set PATH explicitly so npm can be resolved at runtime',
)

assert(
  devCompose.includes('node --version && npm --version'),
  'front development command should print node and npm versions before starting Vite for diagnostics',
)
