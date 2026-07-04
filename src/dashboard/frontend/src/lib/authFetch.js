// Global 401 interceptor — any /api call that comes back unauthenticated
// bounces the browser to the login page. Installed once from main.jsx so
// none of the ~60 fetch call sites need to change.
const _fetch = window.fetch

window.fetch = async (input, init) => {
  const res = await _fetch(input, init)
  const url = typeof input === 'string' ? input : (input && input.url) || ''
  if (
    res.status === 401 &&
    url.startsWith('/api') &&
    !url.startsWith('/api/auth') &&
    !window.location.pathname.startsWith('/dashboard/login')
  ) {
    window.location.href = '/dashboard/login'
  }
  return res
}
