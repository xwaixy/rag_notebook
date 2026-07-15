const TOKEN_KEY = 'jwt_token'

export function getAuthToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
  } else {
    localStorage.removeItem(TOKEN_KEY)
  }
}

export function clearAuthToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function isAuthenticated() {
  return Boolean(getAuthToken())
}

export function getAuthHeaders(extraHeaders = {}) {
  const token = getAuthToken()
  return token
    ? { ...extraHeaders, Authorization: `Bearer ${token}` }
    : { ...extraHeaders }
}

export function getLoginRedirect(currentPath = '') {
  return {
    path: '/login',
    query: currentPath ? { redirect: currentPath } : {},
  }
}
