import { defineStore } from 'pinia';
import axios from 'axios';
import { apiConfig } from '../config/api';
import { clearAuthToken, getAuthHeaders, getAuthToken, setAuthToken } from '../utils/auth';

// 从cookie中获取CSRF token
const getCsrfToken = () => {
  const cookieValue = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrftoken='))
    ?.split('=')[1];
  return cookieValue || '';
};

export const useUserStore = defineStore('user', {
  state: () => ({
    userInfo: null,
    userBio: '这是我的个人简介'
  }),
  
  getters: {
    getUserInfo: (state) => state.userInfo,
    getToken: () => getAuthToken(),
    getLoginStatus: () => Boolean(getAuthToken()),
    getUserBio: (state) => state.userInfo?.bio || state.userBio,
    isSuperuser: (state) => state.userInfo?.is_superuser === true
  },
  
  actions: {
    clearAuthState() {
      this.userInfo = null;
      clearAuthToken();
    },

    async login(userData) {
      try {
        const response = await axios.post(apiConfig.endpoints.login, {
          username: userData.username,
          password: userData.password
        }, {
          headers: {
            'X-CSRFTOKEN': getCsrfToken()
          }
        });
        
        // 检查响应状态
        if (response.status === 200) {
          const userInfo = response.data.user;
          const token = response.data.token;
          
          this.userInfo = userInfo;
          setAuthToken(token);
          
          return {
            success: true,
            message: response.data.message
          };
        } else {
          // 登录失败
          return {
            success: false,
            message: response.data.detail || '登录失败'
          };
        }
      } catch (error) {
        console.error('登录请求失败:', error);
        return {
          success: false,
          message: error.response?.data?.detail?.non_field_errors?.[0] || '登录请求失败，请稍后再试'
        };
      }
    },
    
    async logout() {
      try {
        const token = getAuthToken();
        if (token) {
          await axios.post(apiConfig.endpoints.logout, {}, {
            headers: getAuthHeaders({ 'X-CSRFTOKEN': getCsrfToken() })
          });
        }
      } catch (error) {
        console.error('注销请求失败:', error);
      } finally {
        this.clearAuthState();
      }
    },
    
    // 获取用户信息
    async getUserInfoDetail() {
      try {
        const token = getAuthToken();
        if (!token) {
          this.clearAuthState();
          return {
            success: false,
            message: '未登录'
          };
        }
        
        // 发送获取用户信息请求
        const response = await axios.get(apiConfig.endpoints.profile, {
          headers: getAuthHeaders({ 'X-CSRFTOKEN': getCsrfToken() })
        });
        
        // 检查响应状态
        if (response.status === 200) {
          // 更新用户信息
          this.userInfo = response.data.data;
          
          return {
            success: true,
            message: response.data.message,
            data: response.data.data
          };
        } else {
          return {
            success: false,
            message: response.data.detail || '获取用户信息失败'
          };
        }
      } catch (error) {
        console.error('获取用户信息请求失败:', error);
        if (error.response?.status === 401) {
          this.clearAuthState();
        }
        return {
          success: false,
          message: error.response?.data?.detail || '获取用户信息请求失败，请稍后再试'
        };
      }
    },

    async ensureUserInfo() {
      if (!getAuthToken()) {
        return { success: false, message: '未登录' };
      }

      if (this.userInfo && typeof this.userInfo.is_superuser === 'boolean') {
        return { success: true, data: this.userInfo };
      }

      return this.getUserInfoDetail();
    },
    
    // 更新用户信息
    async updateUserInfo(userData) {
      try {
        const token = getAuthToken();
        if (!token) {
          this.clearAuthState();
          return {
            success: false,
            message: '未登录'
          };
        }
        
        // 发送更新用户信息请求
        const response = await axios.put(apiConfig.endpoints.updateProfile, userData, {
          headers: getAuthHeaders({
            'X-CSRFTOKEN': getCsrfToken(),
            'Content-Type': 'application/json'
          })
        });
        
        // 检查响应状态
        if (response.status === 200) {
          // 更新用户信息
          this.userInfo = response.data.user;
          
          // 如果返回了新的token，更新token
          if (response.data.token) {
            setAuthToken(response.data.token);
          }
          
          return {
            success: true,
            message: response.data.message
          };
        } else {
          return {
            success: false,
            message: response.data.detail || '更新用户信息失败'
          };
        }
      } catch (error) {
        console.error('更新用户信息请求失败:', error);
        if (error.response?.status === 401) {
          this.clearAuthState();
        }
        return {
          success: false,
          message: error.response?.data?.message || error.response?.data?.detail || '更新用户信息请求失败，请稍后再试'
        };
      }
    },
    
    // 更新密码
    async updatePassword(oldPassword, newPassword) {
      try {
        const token = getAuthToken();
        if (!token) {
          this.clearAuthState();
          return {
            success: false,
            message: '未登录'
          };
        }
        
        // 发送更新密码请求
        const response = await axios.post(apiConfig.endpoints.changePassword, {
          old_password: oldPassword,
          new_password: newPassword
        }, {
          headers: getAuthHeaders({
            'X-CSRFTOKEN': getCsrfToken(),
            'Content-Type': 'application/json'
          })
        });
        
        // 检查响应状态
        if (response.status === 200) {
          return {
            success: true,
            message: response.data.message
          };
        } else {
          return {
            success: false,
            message: response.data.detail || '更新密码失败'
          };
        }
      } catch (error) {
        console.error('更新密码请求失败:', error);
        if (error.response?.status === 401) {
          this.clearAuthState();
        }
        return {
          success: false,
          message: error.response?.data?.detail || '更新密码请求失败，请稍后再试'
        };
      }
    },
    
    // 用户注册
    async register(userData) {
      try {
        // 发送注册请求到用户服务
        const response = await axios.post(apiConfig.endpoints.register, {
          username: userData.username,
          email: userData.email,
          telephone: userData.telephone || '',
          password: userData.password,
          confirm_password: userData.confirm_password
        }, {
          headers: {
            'X-CSRFTOKEN': getCsrfToken(),
            'Content-Type': 'application/json'
          }
        });
        
        // 根据后端返回的数据格式判断注册是否成功
        // 后端返回格式: { status: 201, message: "注册成功", user: {...}, token: "..." }
        if (response.data.status === 201 && response.data.token) {
          const token = response.data.token;
          const userInfo = response.data.user;
          
          this.userInfo = userInfo;
          setAuthToken(token);

          return {
            success: true,
            message: response.data.message || '注册成功'
          };
        } else {
          return {
            success: false,
            message: response.data.message || '注册失败'
          };
        }
      } catch (error) {
        console.error('注册请求异常:', error);
        
        // 处理错误响应
        let errorMessage = '注册失败，请稍后重试';
        if (error.response?.data?.message) {
          errorMessage = error.response.data.message;
        } else if (error.response?.data?.detail) {
          errorMessage = error.response.data.detail;
        }
        
        return {
          success: false,
          message: errorMessage
        };
      }
    }
  },
  
  persist: {
    key: 'user-store',
    paths: ['userInfo', 'userBio'],
  }
});
