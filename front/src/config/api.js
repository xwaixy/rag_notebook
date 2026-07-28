/**
 * API配置文件
 * 包含API基础URL和所有API端点配置
 */

// API基础URL配置
export const apiConfig = {
  // 后端API基础URL（使用相对路径，通过Vite代理访问）
  baseURL: import.meta.env.VITE_BASE_URL || '',
  // 用户服务基础URL（使用相对路径，通过Vite代理访问）
  userBaseURL: import.meta.env.VITE_USER_BASE_URL || '',
  
  // API端点配置
  endpoints: {
    // 认证相关
    login: '/api/user/login/',
    logout: '/api/user/logout/',
    register: '/api/user/register/',
    profile: '/api/user/detail/',
    updateProfile: '/api/user/update/',
    changePassword: '/api/user/change_password/',

    // 管理员功能
    adminDashboard: '/api/ops/dashboard/',
    adminUsers: '/api/ops/users/',
    adminUserStatus: (userId) => `/api/ops/users/${userId}/status/`,
    adminBusiness: '/api/ops/business/',
    adminLogs: '/api/ops/logs/',
    
    // 文件上传
    uploadFile: '/api/file/upload/',
    
    // AI对话相关
    agentQuery: '/api/chat/agent/query/stream',
    agentQueryStream: '/api/chat/agent/query/stream',

    // RAG相关
    ragQuery: '/api/chat/rag/query',

    // 会话管理
    getSession: '/api/chat/session/',
    deleteSession: '/api/chat/session/',
    getAllSessions: '/api/chat/sessions',
    getUserSessions: '/api/chat/sessions',

    // 向量数据库
    uploadSingleFile: '/api/knowledge/add/single',
    uploadMultipleFiles: '/api/knowledge/add/multiple',
    uploadMultipleFilesStream: '/api/knowledge/add/multiple/stream',
    knowledgeList: '/api/knowledge/list',
    knowledgeDetail: (filename) => `/api/knowledge/detail?filename=${encodeURIComponent(filename)}`,
    knowledgeChunks: (filename) => `/api/knowledge/chunks?filename=${encodeURIComponent(filename)}`,
    knowledgeDeleteByFilename: '/api/knowledge/delete/filename',
    knowledgeImagesAll: (md5) => `/api/knowledge/images/all/${md5}`,
    cleanVectors: '/api/knowledge/clean',

    // 文档重排序
    reorderDocuments: '/api/chat/reorder',
    
    // 笔记管理
    noteCreate: '/api/note/create',
    noteUpdate: (noteId) => `/api/note/${noteId}`,
    noteDelete: (noteId) => `/api/note/${noteId}`,
    noteDetail: (noteId) => `/api/note/${noteId}`,
    noteList: '/api/note/list',
    noteSearch: '/api/note/search',
    noteAutoTag: (noteId) => `/api/note/${noteId}/auto-tag`,
    noteRelated: (noteId) => `/api/note/${noteId}/related`,
    noteDownload: (noteId) => `/api/note/${noteId}/download`,
    noteAutocomplete: '/api/note/autocomplete',
    noteAssistStream: '/api/note/assist/stream',
    
    // 回顾提醒
    reviewToday: '/api/review/today',
    reviewDone: (noteId) => `/api/review/done/${noteId}`,
    reviewQuestion: (noteId) => `/api/review/question/${noteId}`,
  }
}
