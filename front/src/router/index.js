import { createRouter, createWebHistory } from 'vue-router'
import { showToast } from 'vant'
import { getLoginRedirect, isAuthenticated } from '../utils/auth'

const authMeta = { requiresAuth: true }

const routes = [
  {
    path: '/',
    redirect: '/notes'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: {
      title: '登录',
      keepAlive: false
    }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue'),
    meta: {
      title: '注册',
      keepAlive: false
    }
  },
  {
    path: '/chat',
    name: 'AIChat',
    component: () => import('../views/AIChat.vue'),
    meta: {
      title: 'AI助手',
      keepAlive: true,
      ...authMeta,
    }
  },
  {
    path: '/chat/:sessionId',
    name: 'AIChatWithSession',
    component: () => import('../views/AIChat.vue'),
    meta: {
      title: 'AI助手',
      keepAlive: true,
      ...authMeta,
    }
  },
  // 兼容旧路由
  {
    path: '/aichat',
    redirect: '/chat'
  },
  {
    path: '/aichat/:sessionId',
    redirect: (to) => `/chat/${to.params.sessionId}`
  },
  {
    path: '/my',
    name: 'My',
    component: () => import('../views/My.vue'),
    meta: {
      title: '我的',
      keepAlive: true
    }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('../views/Profile.vue'),
    meta: {
      title: '个人信息',
      keepAlive: false,
      ...authMeta,
    }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/Settings.vue'),
    meta: {
      title: '设置',
      keepAlive: false,
      ...authMeta,
    }
  },
  {
    path: '/aboutus',
    name: 'AboutUs',
    component: () => import('../views/AboutUs.vue'),
    meta: {
      title: '关于我们',
      keepAlive: false
    }
  },
  {
    path: '/knowledge',
    name: 'KnowledgeBase',
    component: () => import('../views/KnowledgeBase.vue'),
    meta: {
      title: '知识库管理',
      keepAlive: false,
      ...authMeta,
    }
  },
  // 兼容旧路由
  {
    path: '/knowledgebase',
    redirect: '/knowledge'
  },
  {
    path: '/sessions',
    name: 'Sessions',
    component: () => import('../views/Sessions.vue'),
    meta: {
      title: '会话管理',
      keepAlive: true,
      ...authMeta,
    }
  },
  {
    path: '/notes',
    name: 'NoteList',
    component: () => import('../views/NoteList.vue'),
    meta: {
      title: '笔记',
      keepAlive: true,
      ...authMeta,
    }
  },
  {
    path: '/notes/:id',
    name: 'NoteEditor',
    component: () => import('../views/NoteEditor.vue'),
    meta: {
      title: '编辑笔记',
      keepAlive: false,
      ...authMeta,
    }
  },
  {
    path: '/review',
    name: 'DailyReview',
    component: () => import('../views/DailyReview.vue'),
    meta: {
      title: '每日回顾',
      keepAlive: false,
      ...authMeta,
    }
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// 全局前置守卫
router.beforeEach((to, from, next) => {
  // 设置页面标题
  document.title = to.meta.title || 'AI Second Brain'

  if (to.matched.some((record) => record.meta.requiresAuth) && !isAuthenticated()) {
    showToast('请先登录')
    next(getLoginRedirect(to.fullPath))
    return
  }

  next()
})

export default router
