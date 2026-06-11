// RBAC navigation guard — implemented in Phase 4b.
// Scaffold placeholder: passes all navigation through unconditionally.
// Replace with real role/permission evaluation against the auth store
// when Phase 4b (Authentication & Authorization) is implemented.

import type { NavigationGuard } from 'vue-router'

export const rbacGuard: NavigationGuard = (_to, _from, next) => {
  next()
}
