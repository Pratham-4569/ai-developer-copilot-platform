import { createRouter, createWebHistory } from 'vue-router'
import { authGuard } from './guards/auth.guard'
import { rbacGuard } from './guards/rbac.guard'
import { authRoutes } from './routes/auth.routes'
import { repositoryRoutes } from './routes/repository.routes'
import { chatRoutes } from './routes/chat.routes'
import { analysisRoutes } from './routes/analysis.routes'
import { dashboardRoutes } from './routes/dashboard.routes'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    ...authRoutes,
    ...repositoryRoutes,
    ...chatRoutes,
    ...analysisRoutes,
    ...dashboardRoutes,
  ],
})

router.beforeEach(authGuard)
router.beforeEach(rbacGuard)

export default router
