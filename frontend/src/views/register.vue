<template>
  <div class="auth-page register-page">
    <main class="auth-shell">
      <section class="auth-art" aria-label="Data Atlas">
        <div class="auth-brand">
          <span class="auth-brand-dot"></span>
          <span>Data Atlas</span>
        </div>

        <div class="auth-art-copy">
          <p>数据与图片智能工作台</p>
          <h1>创建账户，开始工作。</h1>
        </div>

        <div class="auth-art-card" aria-hidden="true">
          <strong>Ready</strong>
          <span>新工作台空间</span>
        </div>

        <div class="auth-symbols" aria-hidden="true">
          <span>⌘</span>
          <span>✦</span>
          <span>⌁</span>
        </div>
      </section>

      <section class="auth-panel" aria-label="注册表单">
        <n-config-provider :theme-overrides="naiveThemeOverrides">
          <div class="auth-form-card">
            <div class="auth-form-head">
              <h2>创建账户</h2>
              <p>注册后使用你的工作台。</p>
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
                @keyup.enter="handleRegister"
              />
            </div>

            <div class="form-group">
              <label class="form-label">密码</label>
              <n-input
                v-model:value="password"
                class="auth-input"
                type="password"
                show-password-on="click"
                autocomplete="new-password"
                placeholder="设置密码"
                @keyup.enter="handleRegister"
              />
              <div v-if="password" class="password-strength" :class="passwordStrength.level" aria-live="polite">
                <div class="password-strength-head">
                  <span>密码强度</span>
                  <strong>{{ passwordStrength.label }}</strong>
                </div>
                <div class="password-strength-meter" aria-hidden="true">
                  <span
                    class="password-strength-bar"
                    :style="{ width: `${passwordStrength.percent}%` }"
                  ></span>
                </div>
              </div>
            </div>

            <div class="form-group">
              <label class="form-label">确认密码</label>
              <n-input
                v-model:value="confirmPassword"
                class="auth-input"
                type="password"
                show-password-on="click"
                autocomplete="new-password"
                placeholder="再次输入密码"
                :aria-invalid="!passwordsMatch"
                @keyup.enter="handleRegister"
              />
              <p v-if="!passwordsMatch" class="password-match-hint">两次输入的密码不一致</p>
            </div>

            <n-button
              class="auth-submit"
              type="primary"
              :loading="loading"
              :disabled="loading"
              @click="handleRegister"
            >
              {{ loading ? "正在注册..." : "注册" }}
            </n-button>

            <div v-if="message" class="auth-message" :class="messageType">
              {{ message }}
            </div>

            <div class="auth-footer">
              <span>已有账户？</span>
              <button class="text-link" type="button" @click="goLogin">登录</button>
            </div>
          </div>
        </n-config-provider>
      </section>
    </main>
  </div>
</template>

<script src="./scripts/register.js"></script>

<style scoped src="./styles/auth.css"></style>
