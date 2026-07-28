import axios from 'axios';
import { apiConfig } from '../config/api';
import { getAuthHeaders } from '../utils/auth';

const requestConfig = () => ({
  headers: getAuthHeaders({ 'Content-Type': 'application/json' })
});

export const adminApi = {
  getDashboard() {
    return axios.get(apiConfig.endpoints.adminDashboard, requestConfig());
  },

  getUsers(params = {}) {
    return axios.get(apiConfig.endpoints.adminUsers, {
      ...requestConfig(),
      params
    });
  },

  updateUserStatus(userId, status) {
    return axios.patch(
      apiConfig.endpoints.adminUserStatus(userId),
      { status },
      requestConfig()
    );
  },

  getBusiness(params = {}) {
    return axios.get(apiConfig.endpoints.adminBusiness, {
      ...requestConfig(),
      params
    });
  },

  getLogs(params = {}) {
    return axios.get(apiConfig.endpoints.adminLogs, {
      ...requestConfig(),
      params
    });
  }
};
