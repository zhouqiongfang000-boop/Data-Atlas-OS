<template>
  <div class="platform-layout" :class="{ 'has-ai-dock': route.path.startsWith('/workspace/data') }">
    <div class="platform-aurora platform-aurora--blue"></div>
    <div class="platform-aurora platform-aurora--violet"></div>
    <div class="platform-aurora platform-aurora--mint"></div>
    <div class="platform-texture"></div>

    <aside class="platform-dock glass-card" aria-label="平台导航">
      <RouterLink class="dock-brand" to="/home" aria-label="返回首页">
        <span class="dock-brand__mark">DA</span>
      </RouterLink>

      <nav class="dock-nav">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="dock-item"
          :class="{ active: isActive(item) }"
          :aria-label="item.label"
        >
          <NIcon size="24">
            <component :is="item.icon" />
          </NIcon>
          <span class="dock-tooltip">{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="dock-spacer"></div>

      <button class="dock-item dock-item--button" type="button" aria-label="退出登录" @click="logout">
        <NIcon size="23">
          <LogOutOutline />
        </NIcon>
        <span class="dock-tooltip">退出登录</span>
      </button>
    </aside>

    <main class="platform-workspace glass-card">
      <div class="platform-workspace__bar" aria-label="工作区状态">
        <div class="workspace-title">
          <span>{{ currentPage.kicker }}</span>
          <strong>{{ currentPage.label }}</strong>
        </div>
        <div class="workspace-pills">
          <span class="workspace-pill">{{ currentRole === "admin" ? "管理员" : "标准工作区" }}</span>
          <span class="workspace-pill workspace-pill--live">Live</span>
        </div>
      </div>

      <div class="platform-layout__content">
        <RouterView v-slot="{ Component, route: childRoute }">
          <Transition name="workspace-flow" mode="out-in">
            <component :is="Component" :key="childRoute.fullPath" />
          </Transition>
        </RouterView>
      </div>
    </main>

    <button
      v-show="showBackToTop"
      type="button"
      class="back-to-top"
      aria-label="返回顶部"
      @click="scrollToTop"
    >
      ↑
    </button>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";
import { NIcon } from "naive-ui";
import {
  AnalyticsOutline,
  HomeOutline,
  ImagesOutline,
  LogOutOutline,
  PersonCircleOutline,
  ShieldCheckmarkOutline,
} from "@vicons/ionicons5";

import api from "../api";

const route = useRoute();
const router = useRouter();
const showBackToTop = ref(false);
const currentRole = ref(localStorage.getItem("role") || "user");

const navItems = computed(() => {
  const items = [
    { to: "/home", label: "首页", kicker: "Home", match: "/home", icon: HomeOutline },
    { to: "/workspace/data", label: "数据工作台", kicker: "Data Workspace", match: "/workspace/data", icon: AnalyticsOutline },
    { to: "/workspace/image", label: "图片工作台", kicker: "Image Studio", match: "/workspace/image", icon: ImagesOutline },
    { to: "/account", label: "个人中心", kicker: "Account", match: "/account", icon: PersonCircleOutline },
  ];

  if (currentRole.value === "admin") {
    items.push({ to: "/admin", label: "管理后台", kicker: "Admin", match: "/admin", icon: ShieldCheckmarkOutline });
  }

  return items;
});

const currentPage = computed(() => navItems.value.find((item) => isActive(item)) || navItems.value[0]);

const isActive = (item) => route.path.startsWith(item.match);

const handleScroll = () => {
  showBackToTop.value = window.scrollY > 320;
};

const scrollToTop = () => {
  window.scrollTo({ top: 0, behavior: "smooth" });
};

const logout = () => {
  localStorage.removeItem("token");
  localStorage.removeItem("role");
  localStorage.removeItem("username");
  router.push("/login");
};

const syncCurrentUser = async () => {
  try {
    const res = await api.get("/me");
    currentRole.value = res.data.role || "user";
    localStorage.setItem("role", currentRole.value);
    localStorage.setItem("username", res.data.username || "");
  } catch (error) {
    // The global interceptor handles expired sessions.
  }
};

onMounted(() => {
  handleScroll();
  syncCurrentUser();
  window.addEventListener("scroll", handleScroll, { passive: true });
});

onBeforeUnmount(() => {
  window.removeEventListener("scroll", handleScroll);
});
</script>

<style scoped>
.platform-layout {
  position: relative;
  min-height: 100vh;
  padding: 24px 24px 24px 112px;
  overflow: clip;
  color: #111827;
  background:
    linear-gradient(135deg, #f8fbff 0%, #eef3f9 42%, #f8f5ff 100%);
  isolation: isolate;
}

.platform-texture {
  position: fixed;
  inset: 0;
  z-index: -4;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(127, 143, 164, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(127, 143, 164, 0.08) 1px, transparent 1px);
  background-size: 44px 44px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.56), transparent 84%);
}

.platform-aurora {
  position: fixed;
  z-index: -5;
  pointer-events: none;
  border-radius: 999px;
  filter: blur(70px);
  opacity: 0.34;
}

.platform-aurora--blue {
  width: 38vw;
  height: 38vw;
  left: -14vw;
  top: -16vw;
  background: #9dccff;
}

.platform-aurora--violet {
  width: 42vw;
  height: 42vw;
  right: -18vw;
  top: 2vw;
  background: #d7c7ff;
}

.platform-aurora--mint {
  width: 36vw;
  height: 36vw;
  right: 6vw;
  bottom: -18vw;
  background: #baf4da;
}

.platform-dock {
  position: fixed;
  left: 24px;
  top: 24px;
  bottom: 24px;
  z-index: 40;
  width: 72px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  border-radius: 32px;
  background: rgba(255, 255, 255, 0.52);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.88),
    0 24px 70px rgba(35, 49, 73, 0.16);
}

.dock-brand,
.dock-item {
  position: relative;
  width: 48px;
  height: 48px;
  display: inline-grid;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.68);
  border-radius: 18px;
  color: #526174;
  background: rgba(255, 255, 255, 0.58);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
  transition:
    transform 0.22s cubic-bezier(0.2, 0.8, 0.2, 1),
    box-shadow 0.22s cubic-bezier(0.2, 0.8, 0.2, 1),
    color 0.22s cubic-bezier(0.2, 0.8, 0.2, 1),
    background 0.22s cubic-bezier(0.2, 0.8, 0.2, 1);
}

.dock-brand {
  color: #ffffff;
  border: 0;
  background: transparent;
  box-shadow: none;
}

.dock-brand__mark {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border-radius: 18px;
  background: linear-gradient(135deg, #0a84ff, #7c6cff 52%, #34c759);
  box-shadow: 0 16px 34px rgba(10, 132, 255, 0.24);
  font-size: 15px;
  font-weight: 900;
}

.dock-nav {
  display: grid;
  gap: 12px;
}

.dock-spacer {
  flex: 1;
}

.dock-item--button {
  border: 0;
}

.dock-item:hover,
.dock-item:focus-visible,
.dock-brand:hover {
  transform: translateY(-4px) scale(1.07);
  color: #0a63c7;
  background: rgba(255, 255, 255, 0.86);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    0 16px 34px rgba(10, 132, 255, 0.18);
}

.dock-item.active {
  color: #ffffff;
  background: linear-gradient(135deg, #0a84ff, #4f9dff);
  box-shadow: 0 18px 38px rgba(10, 132, 255, 0.28);
}

.dock-tooltip {
  position: absolute;
  left: calc(100% + 12px);
  top: 50%;
  z-index: 10;
  min-width: max-content;
  padding: 8px 11px;
  border: 1px solid rgba(255, 255, 255, 0.76);
  border-radius: 999px;
  color: #263548;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 14px 30px rgba(35, 49, 73, 0.12);
  opacity: 0;
  pointer-events: none;
  transform: translate3d(-6px, -50%, 0);
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
  backdrop-filter: blur(18px);
}

.dock-item:hover .dock-tooltip,
.dock-item:focus-visible .dock-tooltip {
  opacity: 1;
  transform: translate3d(0, -50%, 0);
}

.platform-workspace {
  position: relative;
  z-index: 1;
  min-height: calc(100vh - 48px);
  overflow: hidden;
  border-radius: 40px;
  background:
    radial-gradient(circle at 82% 12%, rgba(124, 108, 255, 0.14), transparent 30%),
    radial-gradient(circle at 16% 18%, rgba(10, 132, 255, 0.12), transparent 28%),
    linear-gradient(145deg, rgba(255, 255, 255, 0.78), rgba(247, 250, 255, 0.58));
}

.platform-workspace__bar {
  min-height: 70px;
  padding: 18px 22px 0;
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
}

.workspace-title span {
  display: block;
  margin-bottom: 3px;
  color: #8a97a8;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.workspace-title strong {
  color: #111827;
  font-size: 17px;
}

.workspace-pills {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.workspace-pill {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid rgba(202, 214, 228, 0.56);
  border-radius: 999px;
  color: #526174;
  background: rgba(255, 255, 255, 0.56);
  font-size: 12px;
  font-weight: 760;
}

.workspace-pill--live {
  color: #16763a;
  background: rgba(52, 199, 89, 0.1);
}

.platform-layout__content {
  position: relative;
  z-index: 1;
}

.platform-layout__content :deep(.dashboard-page),
.platform-layout__content :deep(.image-studio),
.platform-layout__content :deep(.user-center),
.platform-layout__content :deep(.admin-dashboard) {
  min-height: auto;
  background: transparent;
}

.platform-layout__content :deep(.app-shell) {
  width: 100%;
  min-height: auto;
  padding: clamp(18px, 2vw, 28px);
}

.back-to-top {
  position: fixed;
  right: 28px;
  bottom: 24px;
  z-index: 50;
  width: 52px;
  height: 52px;
  border: 1px solid rgba(255, 255, 255, 0.74);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.68);
  color: #0a63c7;
  font-size: 22px;
  font-weight: 800;
  box-shadow: 0 16px 34px rgba(35, 49, 73, 0.14);
  backdrop-filter: blur(18px);
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease;
}

.back-to-top:hover {
  transform: translateY(-3px);
  box-shadow: 0 20px 38px rgba(10, 132, 255, 0.22);
}

.platform-layout.has-ai-dock .back-to-top {
  right: 176px;
}

@media (max-width: 900px) {
  .platform-layout {
    padding: 92px 14px 14px;
  }

  .platform-dock {
    top: 14px;
    right: 14px;
    bottom: auto;
    left: 14px;
    width: auto;
    height: 64px;
    padding: 8px 10px;
    flex-direction: row;
    border-radius: 28px;
  }

  .dock-nav {
    display: flex;
    gap: 8px;
    min-width: 0;
    overflow-x: auto;
  }

  .dock-spacer {
    flex: 1 0 6px;
  }

  .dock-brand,
  .dock-brand__mark,
  .dock-item {
    width: 46px;
    height: 46px;
    border-radius: 17px;
    flex: 0 0 auto;
  }

  .dock-tooltip {
    display: none;
  }

  .platform-workspace {
    min-height: calc(100vh - 106px);
    border-radius: 32px;
  }
}

@media (max-width: 640px) {
  .platform-layout {
    padding: 86px 10px 10px;
  }

  .platform-dock {
    height: 60px;
  }

  .dock-brand,
  .dock-brand__mark,
  .dock-item {
    width: 42px;
    height: 42px;
    border-radius: 16px;
  }

  .platform-workspace {
    border-radius: 28px;
  }

  .platform-layout.has-ai-dock .back-to-top {
    right: 16px;
    bottom: 96px;
  }

  .platform-workspace__bar {
    min-height: auto;
    padding: 16px 16px 0;
    align-items: stretch;
    flex-direction: column;
  }

  .workspace-pills {
    justify-content: flex-start;
  }
}
</style>
