import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
const BACKEND_TARGET = process.env.VITE_BACKEND_TARGET || 'http://127.0.0.1:8000';
const USER_TARGET = process.env.VITE_USER_TARGET || 'http://127.0.0.1:8001';

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    host: true, // 允许局域网访问
    proxy: {
      // 后端接口统一走 /api 前缀，避免和前端页面路由冲突。
      '/api/chat': {
        target: BACKEND_TARGET,
        changeOrigin: true,
        ws: true,
        rewrite: (path) => path.replace(/^\/api\/chat/, '/chat')
      },
      '/api/knowledge': {
        target: BACKEND_TARGET,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/knowledge/, '/knowledge')
      },
      '/api/note': {
        target: BACKEND_TARGET,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/note/, '/note')
      },
      '/api/review': {
        target: BACKEND_TARGET,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/review/, '/review')
      },
      '/api/health': {
        target: BACKEND_TARGET,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/health/, '/health')
      },
      // 用户与文件服务代理到 Django。
      '/api/user': {
        target: USER_TARGET,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/user/, '/user')
      },
      '/api/file': {
        target: USER_TARGET,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/file/, '/file')
      },
      '/api/ops': {
        target: USER_TARGET,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/ops/, '/ops')
      }
    }
  }
})
