// Auth navigation guard — implemented in Phase 4b.
// Scaffold placeholder: passes all navigation through unconditionally.
// Replace with real JWT validation, token refresh, and login redirect logic
// when Phase 4b (Authentication & Authorization) is implemented.

import type { NavigationGuard } from 'vue-router'

export const authGuard: NavigationGuard = (_to, _from, next) => {
  next()
}
