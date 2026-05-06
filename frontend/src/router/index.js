import { createRouter, createWebHistory } from "vue-router";

import api from "../api";

const PlatformLayout = () => import("../layouts/PlatformLayout.vue");
const Login = () => import("../views/login.vue");
const Register = () => import("../views/register.vue");
const Home = () => import("../views/Home.vue");
const DataWorkspace = () => import("../views/DataWorkspace.vue");
const ImageWorkspace = () => import("../views/ImageWorkspace.vue");
const UserCenter = () => import("../views/UserCenter.vue");
const AdminDashboard = () => import("../views/AdminDashboard.vue");

const routes = [
  { path: "/", redirect: "/home" },
  { path: "/login", component: Login, meta: { guestOnly: true } },
  { path: "/register", component: Register, meta: { guestOnly: true } },
  {
    path: "/",
    component: PlatformLayout,
    meta: { requiresAuth: true },
    children: [
      { path: "home", component: Home },
      { path: "workspace/data", component: DataWorkspace },
      { path: "workspace/image", component: ImageWorkspace },
      { path: "account", component: UserCenter },
      { path: "admin", component: AdminDashboard, meta: { adminOnly: true } },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0, behavior: "smooth" };
  },
});

const syncCurrentUser = async () => {
  const token = localStorage.getItem("token");
  if (!token) return null;

  try {
    const res = await api.get("/me");
    localStorage.setItem("username", res.data.username || "");
    localStorage.setItem("role", res.data.role || "user");
    return res.data;
  } catch (error) {
    return null;
  }
};

router.beforeEach(async (to) => {
  const token = localStorage.getItem("token");
  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth);
  const guestOnly = to.matched.some((record) => record.meta.guestOnly);
  const adminOnly = to.matched.some((record) => record.meta.adminOnly);

  if (requiresAuth && !token) {
    return "/login";
  }

  if (guestOnly && token) {
    return "/home";
  }

  if (adminOnly) {
    let role = localStorage.getItem("role");
    if (!role) {
      const user = await syncCurrentUser();
      role = user?.role;
    }

    if (role !== "admin") {
      return "/home";
    }
  }

  return true;
});

export default router;
