/**
 * Vue Router 配置
 */
import { createRouter, createWebHistory } from 'vue-router'

// 使用动态导入实现路由懒加载
const Dashboard = () => import('@/views/Dashboard.vue')
const Settings = () => import('@/views/Settings.vue')
const History = () => import('@/views/History.vue')
const Events = () => import('@/views/Events.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: Dashboard
    },
    {
      path: '/settings',
      name: 'settings',
      component: Settings
    },
    {
      path: '/history',
      name: 'history',
      component: History
    },
    {
      path: '/events',
      name: 'events',
      component: Events
    }
  ]
})

export default router
