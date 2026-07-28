<template>
  <div class="admin-container">
    <van-nav-bar
      fixed
      left-arrow
      title="管理中心"
      @click-left="goBack"
      @click-right="refreshCurrentTab"
    >
      <template #right>
        <van-icon name="replay" size="19" />
      </template>
    </van-nav-bar>

    <main class="admin-content">
      <van-tabs v-model:active="activeTab" sticky :offset-top="46" @change="handleTabChange">
        <van-tab title="概览" name="overview">
          <section class="welcome-card panel-card">
            <div>
              <span class="eyebrow">ADMIN CONSOLE</span>
              <h1>系统运行概览</h1>
              <p>集中查看服务状态、用户规模和最近业务活动。</p>
            </div>
            <div class="welcome-mark">
              <van-icon name="shield-o" />
            </div>
          </section>

          <div v-if="dashboardLoading" class="loading-state">加载中...</div>
          <template v-else>
            <div class="stats-grid">
              <div v-for="stat in statCards" :key="stat.key" class="stat-card">
                <div class="stat-icon"><van-icon :name="stat.icon" /></div>
                <div class="stat-content">
                  <strong class="stat-value">{{ stat.value }}</strong>
                  <span class="stat-label">{{ stat.label }}</span>
                </div>
              </div>
            </div>

            <section class="dashboard-columns">
              <div class="panel-card status-panel">
                <div class="section-heading">
                  <div>
                    <h2>服务状态</h2>
                    <p>核心依赖的实时连通情况</p>
                  </div>
                  <span class="summary-pill">{{ healthyCheckCount }}/{{ dashboard.checks.length }} 正常</span>
                </div>
                <div v-if="dashboard.checks.length" class="status-list">
                  <div
                    v-for="(check, index) in dashboard.checks"
                    :key="`${check.label || check.name || 'check'}-${index}`"
                    class="status-row"
                  >
                    <span class="status-dot" :class="checkStateClass(check)"></span>
                    <div class="status-info">
                      <strong>{{ check.label || check.name || '服务检查' }}</strong>
                      <span>{{ check.message || check.detail || '暂无详情' }}</span>
                    </div>
                    <span class="status-badge" :class="checkStateClass(check)">
                      {{ checkStateLabel(check) }}
                    </span>
                  </div>
                </div>
                <van-empty v-else image-size="64" description="暂无状态数据" />
              </div>

              <div class="panel-card activity-panel">
                <div class="section-heading">
                  <div>
                    <h2>最近活动</h2>
                    <p>会话、笔记和消息更新</p>
                  </div>
                </div>
                <div v-if="recentActivities.length" class="activity-list">
                  <div v-for="activity in recentActivities" :key="activity.key" class="activity-row">
                    <div class="activity-icon"><van-icon :name="activity.icon" /></div>
                    <div class="activity-content">
                      <strong>{{ activity.title }}</strong>
                      <span>{{ activity.meta }}</span>
                    </div>
                    <time>{{ activity.time }}</time>
                  </div>
                </div>
                <van-empty v-else image-size="64" description="暂无最近活动" />
              </div>
            </section>
          </template>
        </van-tab>

        <van-tab title="用户" name="users">
          <section class="section-shell">
            <div class="section-heading page-heading">
              <div>
                <span class="eyebrow">USER MANAGEMENT</span>
                <h2>用户管理</h2>
                <p>共 {{ userTotal }} 位用户，每页显示 {{ userPageSize }} 条</p>
              </div>
            </div>

            <div class="filter-card panel-card">
              <label class="filter-control filter-search">
                <span>关键词</span>
                <div class="input-with-icon">
                  <van-icon name="search" />
                  <input
                    v-model="userSearch"
                    class="filter-input"
                    type="search"
                    placeholder="用户名、邮箱或手机号"
                    @keyup.enter="searchUsers"
                  />
                </div>
              </label>
              <label class="filter-control">
                <span>用户状态</span>
                <select v-model="userStatus" class="filter-select" @change="searchUsers">
                  <option value="">全部状态</option>
                  <option value="0">未激活</option>
                  <option value="1">已激活</option>
                  <option value="2">已锁定</option>
                </select>
              </label>
              <div class="filter-actions">
                <van-button size="small" plain @click="resetUserFilters">重置</van-button>
                <van-button size="small" type="primary" icon="search" @click="searchUsers">查询</van-button>
              </div>
            </div>

            <div v-if="usersLoading" class="loading-state panel-card">加载中...</div>
            <div v-else-if="users.length" class="user-grid">
              <article v-for="user in users" :key="user.id" class="user-card panel-card">
                <div class="user-card-main">
                  <div class="user-avatar">{{ (user.username || '?')[0].toUpperCase() }}</div>
                  <div class="user-identity">
                    <div class="user-name-line">
                      <strong>{{ user.username }}</strong>
                      <span v-if="user.is_superuser" class="admin-label">管理员</span>
                    </div>
                    <span>{{ user.email || '未填写邮箱' }}</span>
                    <span>{{ user.telephone || '未填写手机号' }}</span>
                  </div>
                </div>
                <div class="user-card-footer">
                  <span class="status-badge" :class="userStatusClass(user)">
                    {{ user.status_label || fallbackStatusLabel(user.status) }}
                  </span>
                  <span class="joined-time">注册于 {{ formatDate(user.date_joined) }}</span>
                  <van-button
                    v-if="!user.is_superuser"
                    size="mini"
                    plain
                    :type="user.is_active ? 'warning' : 'primary'"
                    @click="toggleUser(user)"
                  >
                    {{ user.is_active ? '停用' : '启用' }}
                  </van-button>
                </div>
              </article>
            </div>
            <van-empty v-else description="暂无符合条件的用户" />

            <div v-if="userTotal > userPageSize" class="pagination-panel panel-card">
              <span>{{ userPageRange }}</span>
              <van-pagination
                v-model="userPage"
                :total-items="userTotal"
                :items-per-page="userPageSize"
                :show-page-size="5"
                force-ellipses
                @change="loadUsers"
              />
            </div>
          </section>
        </van-tab>

        <van-tab title="业务数据" name="business">
          <section class="section-shell">
            <div class="section-heading page-heading">
              <div>
                <span class="eyebrow">BUSINESS DATA</span>
                <h2>业务数据</h2>
                <p>当前共 {{ businessTotal }} 条记录，每页固定加载 {{ businessPageSize }} 条</p>
              </div>
            </div>

            <div class="resource-switcher panel-card">
              <button
                v-for="resource in businessResources"
                :key="resource.value"
                type="button"
                class="resource-button"
                :class="{ active: businessResource === resource.value }"
                @click="selectBusinessResource(resource.value)"
              >
                <van-icon :name="resource.icon" />
                <span>{{ resource.label }}</span>
              </button>
            </div>

            <div class="filter-card panel-card business-filter">
              <label class="filter-control filter-search">
                <span>搜索当前分类</span>
                <div class="input-with-icon">
                  <van-icon name="search" />
                  <input
                    v-model="businessSearch"
                    class="filter-input"
                    type="search"
                    :placeholder="businessSearchPlaceholder"
                    @keyup.enter="searchBusiness"
                  />
                </div>
              </label>
              <div class="filter-actions">
                <van-button size="small" plain @click="resetBusinessSearch">重置</van-button>
                <van-button size="small" type="primary" icon="search" @click="searchBusiness">查询</van-button>
              </div>
            </div>

            <div v-if="businessLoading" class="loading-state panel-card">加载中...</div>
            <div v-else-if="businessItems.length" class="business-list">
              <article
                v-for="(item, index) in businessItems"
                :key="`${businessResource}-${item.id || index}`"
                class="business-card panel-card"
              >
                <div class="business-card-icon">
                  <van-icon :name="currentBusinessResource.icon" />
                </div>
                <div class="business-card-content">
                  <div class="business-title-line">
                    <strong>{{ businessTitle(item) }}</strong>
                    <span>#{{ (businessPage - 1) * businessPageSize + index + 1 }}</span>
                  </div>
                  <div class="business-meta-grid">
                    <div v-for="entry in businessMeta(item)" :key="entry.label" class="meta-item">
                      <span>{{ entry.label }}</span>
                      <strong>{{ entry.value }}</strong>
                    </div>
                  </div>
                </div>
              </article>
            </div>
            <van-empty v-else description="暂无符合条件的业务数据" />

            <div v-if="businessTotal > businessPageSize" class="pagination-panel panel-card">
              <span>{{ businessPageRange }}</span>
              <van-pagination
                v-model="businessPage"
                :total-items="businessTotal"
                :items-per-page="businessPageSize"
                :show-page-size="5"
                force-ellipses
                @change="loadBusiness"
              />
            </div>
          </section>
        </van-tab>

        <van-tab title="日志" name="logs">
          <section class="section-shell">
            <div class="section-heading page-heading">
              <div>
                <span class="eyebrow">LOG VIEWER</span>
                <h2>后端日志</h2>
                <p>查看 FastAPI 最近输出，默认展示最后 200 行</p>
              </div>
            </div>

            <div class="log-toolbar panel-card">
              <label class="filter-control log-select">
                <span>日志文件</span>
                <select v-model="selectedLog" class="filter-select" @change="loadLogs">
                  <option value="">选择日志文件</option>
                  <option v-for="file in logs.files" :key="file.name" :value="file.name">
                    {{ file.name }} · {{ formatFileSize(file.size) }}
                  </option>
                </select>
              </label>
              <van-button size="small" type="primary" icon="replay" @click="loadLogs">刷新日志</van-button>
            </div>

            <div class="terminal panel-card">
              <div class="terminal-bar">
                <div class="terminal-dots"><i></i><i></i><i></i></div>
                <span>{{ logs.selected || '未选择日志文件' }}</span>
                <small>{{ logLineCount }} 行</small>
              </div>
              <div v-if="logsLoading" class="loading-state terminal-loading">加载中...</div>
              <pre v-else class="log-content">{{ logs.content || '暂无日志内容' }}</pre>
            </div>
          </section>
        </van-tab>
      </van-tabs>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { showDialog, showToast } from 'vant';
import { useRouter } from 'vue-router';
import { adminApi } from '../api/admin';
import { useUserStore } from '../store/user';

const router = useRouter();
const userStore = useUserStore();

const activeTab = ref('overview');
const dashboardLoading = ref(false);
const usersLoading = ref(false);
const businessLoading = ref(false);
const logsLoading = ref(false);

const dashboard = ref({
  stats: {},
  checks: [],
  recent: {
    users: [],
    sessions: [],
    notes: [],
    reviews: [],
    messages: []
  }
});

const users = ref([]);
const userSearch = ref('');
const userStatus = ref('');
const userPage = ref(1);
const userPageSize = 20;
const userTotal = ref(0);

const businessResources = [
  { value: 'sessions', label: '会话', icon: 'chat-o', placeholder: '按会话 ID、标题或用户 ID 搜索' },
  { value: 'messages', label: '消息', icon: 'comment-o', placeholder: '按消息 ID、会话 ID 或角色搜索' },
  { value: 'notes', label: '笔记', icon: 'notes-o', placeholder: '按笔记 ID、标题或用户 ID 搜索' },
  { value: 'reviews', label: '回顾', icon: 'clock-o', placeholder: '按记录 ID、笔记 ID 或用户 ID 搜索' }
];
const businessResource = ref('sessions');
const businessSearch = ref('');
const businessItems = ref([]);
const businessPage = ref(1);
const businessPageSize = 20;
const businessTotal = ref(0);

const logs = ref({ files: [], selected: '', content: '' });
const selectedLog = ref('');

const statCards = computed(() => [
  { key: 'users', label: '用户总数', value: dashboard.value.stats.users ?? 0, icon: 'friends-o' },
  { key: 'active_users', label: '活跃用户', value: dashboard.value.stats.active_users ?? 0, icon: 'passed' },
  { key: 'sessions', label: '会话总数', value: dashboard.value.stats.sessions ?? 0, icon: 'chat-o' },
  { key: 'messages', label: '消息总数', value: dashboard.value.stats.messages ?? 0, icon: 'comment-o' },
  { key: 'notes', label: '笔记总数', value: dashboard.value.stats.notes ?? 0, icon: 'notes-o' },
  { key: 'review_records', label: '回顾记录', value: dashboard.value.stats.review_records ?? 0, icon: 'clock-o' }
]);

const healthyCheckCount = computed(() => dashboard.value.checks.filter(isHealthyCheck).length);
const currentBusinessResource = computed(() => (
  businessResources.find((item) => item.value === businessResource.value) || businessResources[0]
));
const businessSearchPlaceholder = computed(() => currentBusinessResource.value.placeholder);
const userPageRange = computed(() => pageRange(userPage.value, userPageSize, userTotal.value));
const businessPageRange = computed(() => pageRange(businessPage.value, businessPageSize, businessTotal.value));
const logLineCount = computed(() => logs.value.content ? logs.value.content.split('\n').filter(Boolean).length : 0);
const recentActivities = computed(() => buildRecentActivities(dashboard.value.recent));

const goBack = () => router.back();

const handleApiError = (error) => {
  const status = error.response?.status;
  if (status === 401) {
    userStore.clearAuthState();
    showToast('登录状态已失效，请重新登录');
    router.replace('/login');
    return;
  }
  if (status === 403) {
    showToast('只有管理员可以访问此功能');
    router.replace('/my');
    return;
  }
  showToast(error.response?.data?.detail || '管理数据加载失败');
};

const loadDashboard = async () => {
  dashboardLoading.value = true;
  try {
    dashboard.value = (await adminApi.getDashboard()).data.data;
  } catch (error) {
    handleApiError(error);
  } finally {
    dashboardLoading.value = false;
  }
};

const loadUsers = async () => {
  usersLoading.value = true;
  try {
    const response = await adminApi.getUsers({
      page: userPage.value,
      page_size: userPageSize,
      search: userSearch.value.trim(),
      status: userStatus.value
    });
    const data = response.data.data;
    users.value = data.items;
    userTotal.value = data.total;
  } catch (error) {
    handleApiError(error);
  } finally {
    usersLoading.value = false;
  }
};

const searchUsers = () => {
  userPage.value = 1;
  loadUsers();
};

const resetUserFilters = () => {
  userSearch.value = '';
  userStatus.value = '';
  searchUsers();
};

const toggleUser = async (user) => {
  const nextStatus = user.is_active ? 0 : 1;
  const action = nextStatus === 1 ? '启用' : '停用';
  try {
    await showDialog({
      title: `确认${action}用户`,
      message: `确定要${action}用户「${user.username}」吗？`,
      showCancelButton: true
    });
    const response = await adminApi.updateUserStatus(user.id, nextStatus);
    const updated = response.data.data;
    const index = users.value.findIndex((item) => item.id === user.id);
    if (index !== -1) users.value[index] = updated;
    showToast(`${action}成功`);
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') handleApiError(error);
  }
};

const loadBusiness = async () => {
  businessLoading.value = true;
  try {
    const response = await adminApi.getBusiness({
      resource: businessResource.value,
      page: businessPage.value,
      page_size: businessPageSize,
      search: businessSearch.value.trim()
    });
    const data = response.data.data;
    businessItems.value = data.items;
    businessTotal.value = data.total;
  } catch (error) {
    handleApiError(error);
  } finally {
    businessLoading.value = false;
  }
};

const selectBusinessResource = (resource) => {
  if (businessResource.value === resource) return;
  businessResource.value = resource;
  businessSearch.value = '';
  businessPage.value = 1;
  loadBusiness();
};

const searchBusiness = () => {
  businessPage.value = 1;
  loadBusiness();
};

const resetBusinessSearch = () => {
  businessSearch.value = '';
  searchBusiness();
};

const loadLogs = async () => {
  logsLoading.value = true;
  try {
    const params = selectedLog.value ? { file: selectedLog.value } : {};
    const response = await adminApi.getLogs(params);
    logs.value = response.data.data;
    selectedLog.value = logs.value.selected || selectedLog.value;
  } catch (error) {
    handleApiError(error);
  } finally {
    logsLoading.value = false;
  }
};

const handleTabChange = (name) => {
  if (name === 'users' && !users.value.length) loadUsers();
  if (name === 'business' && !businessItems.value.length) loadBusiness();
  if (name === 'logs' && !logs.value.content) loadLogs();
};

const refreshCurrentTab = () => {
  const actions = {
    overview: loadDashboard,
    users: loadUsers,
    business: loadBusiness,
    logs: loadLogs
  };
  actions[activeTab.value]?.();
};

const fallbackStatusLabel = (status) => ({ 0: '未激活', 1: '已激活', 2: '已锁定' }[status] || `状态 ${status}`);

const userStatusClass = (user) => (user.is_active ? 'status-success' : 'status-warning');

const isHealthyCheck = (check) => {
  const state = String(check.status || '').toLowerCase();
  return check.ok === true || ['ok', 'healthy', 'success', 'up'].includes(state);
};

const checkStateClass = (check) => {
  return isHealthyCheck(check) ? 'status-success' : 'status-warning';
};

const checkStateLabel = (check) => (isHealthyCheck(check) ? '正常' : '异常');

const fieldLabels = {
  id: '记录 ID',
  user_id: '用户 ID',
  session_id: '会话 ID',
  note_id: '笔记 ID',
  role: '消息角色',
  created_at: '创建时间',
  updated_at: '更新时间',
  next_review_at: '下次回顾'
};

const formatDate = (value, includeTime = false) => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    ...(includeTime ? { hour: '2-digit', minute: '2-digit' } : {})
  }).format(date);
};

const formatValue = (field, value) => {
  if (value === null || value === undefined || value === '') return '-';
  if (field.endsWith('_at') || field.endsWith('_time')) return formatDate(value, true);
  const text = String(value);
  return text.length > 34 ? `${text.slice(0, 16)}...${text.slice(-10)}` : text;
};

const pageRange = (page, pageSize, total) => {
  if (!total) return '暂无数据';
  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);
  return `第 ${start}-${end} 条，共 ${total} 条`;
};

const businessTitle = (item) => {
  if (item.title) return item.title;
  if (businessResource.value === 'messages') return `${item.role || '未知角色'}消息`;
  if (businessResource.value === 'reviews') return `回顾记录 ${formatValue('id', item.id)}`;
  return `${currentBusinessResource.value.label}记录 ${formatValue('id', item.id)}`;
};

const businessMeta = (item) => Object.entries(item)
  .filter(([field, value]) => field !== 'title' && value !== null && value !== undefined && value !== '')
  .map(([field, value]) => ({
    label: fieldLabels[field] || field,
    value: formatValue(field, value)
  }));

const formatFileSize = (bytes) => {
  if (!Number.isFinite(bytes)) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
};

const buildRecentActivities = (recent) => {
  const groups = [
    ['sessions', 'chat-o', '会话', 'updated_at'],
    ['notes', 'notes-o', '笔记', 'updated_at'],
    ['messages', 'comment-o', '消息', 'created_at'],
    ['reviews', 'clock-o', '回顾', 'next_review_at']
  ];
  return groups.flatMap(([key, icon, label, timeField]) => (
    (recent[key] || []).map((item) => ({
      key: `${key}-${item.id}`,
      icon,
      title: item.title || `${label} ${formatValue('id', item.id)}`,
      meta: item.user_id ? `用户 ${formatValue('user_id', item.user_id)}` : label,
      time: formatDate(item[timeField], true),
      timestamp: new Date(item[timeField] || 0).getTime()
    }))
  )).sort((a, b) => b.timestamp - a.timestamp).slice(0, 8);
};

onMounted(loadDashboard);
</script>

<style scoped>
.admin-container {
  min-height: 100vh;
  padding-top: 46px;
  background: var(--color-bg);
  color: var(--color-text);
}

.admin-content {
  padding-bottom: 24px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  padding: 16px;
}

.stat-card,
.filter-card,
.resource-switcher,
.log-toolbar {
  background: var(--color-card);
  border-radius: 12px;
  box-shadow: 0 1px 4px var(--color-shadow);
}

.stat-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px;
}

.stat-label {
  color: var(--color-text-lighter);
  font-size: 13px;
}

.stat-value {
  color: var(--color-primary);
  font-size: 24px;
  font-family: var(--font-heading);
}

.recent-group {
  margin-top: 14px;
}

.loading-state {
  padding: 48px 16px;
  color: var(--color-text-lighter);
  text-align: center;
}

.filter-card,
.log-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 16px;
  padding: 10px;
}

.filter-input,
.filter-select {
  min-width: 0;
  height: 34px;
  padding: 0 10px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 13px;
}

.filter-input {
  flex: 1;
}

.user-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-badge,
.admin-label {
  display: inline-block;
  padding: 3px 7px;
  border-radius: 999px;
  font-size: 12px;
  white-space: nowrap;
}

.status-success {
  color: #287a4b;
  background: #e7f6ec;
}

.status-warning {
  color: #a56412;
  background: #fff3df;
}

.admin-label {
  color: var(--color-primary);
  background: var(--color-surface);
}

.load-more {
  margin: 16px;
}

.resource-switcher {
  display: flex;
  gap: 8px;
  margin: 16px;
  padding: 10px;
  overflow-x: auto;
}

.resource-switcher .van-button {
  flex-shrink: 0;
}

.log-content {
  min-height: 260px;
  margin: 16px;
  padding: 14px;
  overflow: auto;
  border-radius: 12px;
  background: #29251f;
  color: #f6ead8;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.admin-content :deep(.van-tabs__nav) {
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 1px 0 var(--color-border-light);
}

.admin-content :deep(.van-tabs__content) {
  padding-bottom: 12px;
}

.panel-card {
  background: var(--color-card);
  border: 1px solid var(--color-border-light);
  border-radius: 16px;
  box-shadow: 0 8px 24px var(--color-shadow);
}

.section-shell {
  padding: 18px 16px 8px;
}

.eyebrow {
  display: block;
  margin-bottom: 5px;
  color: var(--color-primary);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.4px;
}

.welcome-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin: 18px 16px 0;
  padding: 22px;
  overflow: hidden;
  background: linear-gradient(135deg, #fffaf2 0%, #f8ead7 100%);
}

.welcome-card h1,
.section-heading h2 {
  margin: 0;
}

.welcome-card h1 {
  font-size: 22px;
}

.welcome-card p,
.section-heading p {
  margin: 5px 0 0;
  color: var(--color-text-lighter);
  font-size: 12px;
}

.welcome-mark {
  display: grid;
  flex: 0 0 62px;
  height: 62px;
  place-items: center;
  border-radius: 20px;
  background: rgba(212, 145, 74, 0.14);
  color: var(--color-primary);
  font-size: 30px;
  transform: rotate(4deg);
}

.stats-grid {
  padding-top: 12px;
}

.stat-card {
  flex-direction: row;
  align-items: center;
  gap: 12px;
  min-height: 66px;
  border: 1px solid var(--color-border-light);
  border-radius: 14px;
  background: var(--color-card);
}

.stat-icon,
.activity-icon,
.business-card-icon {
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 12px;
  background: var(--color-surface);
  color: var(--color-primary);
}

.stat-icon {
  width: 38px;
  height: 38px;
  font-size: 20px;
}

.stat-content {
  display: flex;
  min-width: 0;
  flex-direction: column;
}

.stat-value {
  line-height: 1.15;
}

.dashboard-columns {
  display: grid;
  gap: 14px;
  padding: 0 16px 18px;
}

.status-panel,
.activity-panel {
  padding: 18px;
}

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.page-heading {
  margin: 2px 2px 16px;
}

.section-heading h2 {
  font-size: 18px;
}

.summary-pill {
  padding: 5px 9px;
  border-radius: 999px;
  background: #e7f6ec;
  color: #287a4b;
  font-size: 11px;
  white-space: nowrap;
}

.status-list,
.activity-list {
  margin-top: 14px;
}

.status-row,
.activity-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 0;
  border-top: 1px solid var(--color-border-light);
}

.status-dot {
  width: 8px;
  height: 8px;
  padding: 0;
  border-radius: 50%;
}

.status-info,
.activity-content {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
}

.status-info strong,
.activity-content strong {
  overflow: hidden;
  color: var(--color-text);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-info span,
.activity-content span,
.activity-row time {
  overflow: hidden;
  color: var(--color-text-lighter);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-icon {
  width: 34px;
  height: 34px;
  font-size: 17px;
}

.activity-row time {
  flex: 0 0 auto;
  max-width: 112px;
}

.filter-card,
.log-toolbar {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  margin: 0 0 14px;
  padding: 14px;
}

.filter-control {
  display: flex;
  min-width: 130px;
  flex-direction: column;
  gap: 6px;
}

.filter-control > span {
  color: var(--color-text-lighter);
  font-size: 11px;
  font-weight: 500;
}

.filter-search,
.log-select {
  flex: 1;
}

.input-with-icon {
  display: flex;
  align-items: center;
  gap: 7px;
  height: 38px;
  padding: 0 11px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background: var(--color-surface);
  color: var(--color-text-lighter);
}

.input-with-icon:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(212, 145, 74, 0.1);
}

.filter-input {
  width: 100%;
  height: 100%;
  padding: 0;
  border: 0;
  outline: none;
  background: transparent;
}

.filter-select {
  width: 100%;
  height: 38px;
  border-radius: 10px;
  outline: none;
}

.filter-actions {
  display: flex;
  gap: 8px;
  flex: 0 0 auto;
}

.user-grid,
.business-list {
  display: grid;
  gap: 10px;
}

.user-card,
.business-card {
  padding: 14px;
}

.user-card-main,
.user-card-footer,
.user-name-line,
.business-title-line {
  display: flex;
  align-items: center;
}

.user-card-main {
  gap: 12px;
}

.user-avatar {
  display: grid;
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  place-items: center;
  border: 1px solid #edd3b4;
  border-radius: 14px;
  background: #fff6e9;
  color: var(--color-primary);
  font-family: var(--font-heading);
  font-size: 18px;
  font-weight: 700;
}

.user-identity {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
}

.user-name-line {
  gap: 7px;
}

.user-name-line strong {
  color: var(--color-text);
  font-size: 15px;
}

.user-identity > span,
.joined-time {
  overflow: hidden;
  color: var(--color-text-lighter);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-card-footer {
  gap: 8px;
  margin-top: 13px;
  padding-top: 11px;
  border-top: 1px solid var(--color-border-light);
}

.joined-time {
  flex: 1;
}

.resource-switcher {
  display: grid;
  grid-template-columns: repeat(4, minmax(74px, 1fr));
  gap: 8px;
  margin: 0 0 14px;
  padding: 8px;
  overflow: visible;
}

.resource-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 42px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--color-text-lighter);
  cursor: pointer;
  font-family: var(--font-body);
}

.resource-button.active {
  background: var(--color-primary);
  color: #fff;
  box-shadow: 0 5px 14px rgba(212, 145, 74, 0.24);
}

.business-filter {
  align-items: flex-end;
}

.business-card {
  display: flex;
  gap: 12px;
}

.business-card-icon {
  width: 40px;
  height: 40px;
  font-size: 19px;
}

.business-card-content {
  min-width: 0;
  flex: 1;
}

.business-title-line {
  justify-content: space-between;
  gap: 10px;
}

.business-title-line strong {
  overflow: hidden;
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.business-title-line > span {
  color: var(--color-text-lightest);
  font-size: 11px;
}

.business-meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 7px 12px;
  margin-top: 10px;
}

.meta-item {
  display: flex;
  min-width: 0;
  flex-direction: column;
}

.meta-item span {
  color: var(--color-text-lightest);
  font-size: 10px;
}

.meta-item strong {
  overflow: hidden;
  color: var(--color-text-light);
  font-size: 11px;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pagination-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-top: 14px;
  padding: 11px 14px;
}

.pagination-panel > span {
  color: var(--color-text-lighter);
  font-size: 11px;
  white-space: nowrap;
}

.pagination-panel :deep(.van-pagination__item) {
  min-width: 34px;
  height: 34px;
  color: var(--color-text-light);
  background: var(--color-surface);
}

.pagination-panel :deep(.van-pagination__item--active) {
  color: #fff;
  background: var(--color-primary);
}

.log-toolbar {
  align-items: flex-end;
}

.terminal {
  overflow: hidden;
  border-color: #3d3933;
  background: #27241f;
}

.terminal-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 40px;
  padding: 0 14px;
  background: #34302a;
  color: #d8cbbb;
  font-size: 11px;
}

.terminal-bar > span {
  overflow: hidden;
  flex: 1;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.terminal-bar small {
  color: #9f9385;
}

.terminal-dots {
  display: flex;
  gap: 5px;
}

.terminal-dots i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #d66b5d;
}

.terminal-dots i:nth-child(2) { background: #d8a84f; }
.terminal-dots i:nth-child(3) { background: #6fa678; }

.terminal .log-content {
  min-height: 360px;
  max-height: 62vh;
  margin: 0;
  border-radius: 0;
  background: transparent;
}

.terminal-loading {
  color: #d8cbbb;
}

@media (min-width: 600px) {
  .admin-content {
    max-width: 1080px;
    margin: 0 auto;
  }

  .stats-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .dashboard-columns {
    grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  }

  .user-grid,
  .business-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 599px) {
  .filter-card,
  .log-toolbar,
  .pagination-panel {
    align-items: stretch;
    flex-direction: column;
  }

  .filter-actions {
    justify-content: flex-end;
  }

  .resource-switcher {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .pagination-panel > span {
    text-align: center;
  }

  .pagination-panel :deep(.van-pagination) {
    width: 100%;
  }

  .activity-row time {
    display: none;
  }
}
</style>
