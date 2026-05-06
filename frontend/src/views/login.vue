<template>
  <div class="auth-page login-page">
    <main class="auth-shell">
      <section class="auth-art" aria-label="Data Atlas">
        <div class="auth-brand">
          <span class="auth-brand-dot"></span>
          <span>Data Atlas</span>
        </div>

        <div class="auth-art-copy">
          <p>数据与图片智能工作台</p>
          <h1>让数据与图片处理更轻盈。</h1>
        </div>

        <div class="auth-art-card" aria-hidden="true">
          <strong>98%</strong>
          <span>工作流已准备就绪</span>
        </div>

        <div class="auth-symbols" aria-hidden="true">
          <span>⌘</span>
          <span>✦</span>
          <span>⌁</span>
        </div>
      </section>

      <section class="auth-panel" aria-label="登录表单">
        <n-config-provider :theme-overrides="naiveThemeOverrides">
          <div class="auth-form-card">
            <div class="auth-form-head">
              <h2>欢迎回来</h2>
              <p>登录你的工作台。</p>
            </div>

            <div class="form-group">
              <label class="form-label">用户名</label>
              <n-input
                v-model:value="username"
                class="auth-input"
                type="text"
                autocomplete="username"
                placeholder="输入用户名"
                clearable
                @keyup.enter="handleLogin"
              />
            </div>

            <div class="form-group">
              <label class="form-label">密码</label>
              <n-input
                v-model:value="password"
                class="auth-input"
                type="password"
                show-password-on="click"
                autocomplete="current-password"
                placeholder="输入密码"
                @keyup.enter="handleLogin"
              />
            </div>

            <n-button
              class="auth-submit"
              type="primary"
              :loading="loading"
              :disabled="loading"
              @click="handleLogin"
            >
              {{ loading ? "正在登录..." : "登录" }}
            </n-button>

            <div v-if="message" class="auth-message" :class="messageType">
              {{ message }}
            </div>

            <div class="auth-footer">
              <span>还没有账户？</span>
              <button class="text-link" type="button" @click="goRegister">注册</button>
            </div>
          </div>
        </n-config-provider>
      </section>
    </main>
  </div>
</template>

<script src="./scripts/login.js"></script>

<style scoped src="./styles/auth.css"></style>
