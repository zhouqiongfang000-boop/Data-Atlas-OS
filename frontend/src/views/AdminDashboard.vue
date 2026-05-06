<template>
  <div class="admin-dashboard page-enter">
    <div class="app-shell admin-dashboard__shell">
      <section class="admin-hero">
        <div>
          <span class="admin-eyebrow">ADMIN CENTER</span>
          <h1>管理员后台</h1>
          <p>集中查看用户、角色和平台资产状态，普通分析流程仍保留在各自工作台里。</p>
        </div>
        <button class="btn btn-secondary" :disabled="loading" @click="loadAdminData">
          {{ loading ? "同步中..." : "刷新数据" }}
        </button>
      </section>

      <section class="admin-metrics">
        <article class="admin-metric">
          <span>用户总数</span>
          <strong>{{ summary.total_users }}</strong>
        </article>
        <article class="admin-metric">
          <span>启用用户</span>
          <strong>{{ summary.active_users }}</strong>
        </article>
        <article class="admin-metric">
          <span>管理员</span>
          <strong>{{ summary.admin_users }}</strong>
        </article>
        <article class="admin-metric">
          <span>数据 / 图片</span>
          <strong>{{ summary.file_count }} / {{ summary.image_count }}</strong>
        </article>
        <article class="admin-metric">
          <span>分析记录</span>
          <strong>{{ summary.analysis_count }}</strong>
        </article>
      </section>

      <section class="admin-panel">
        <div class="admin-panel__head">
          <div>
            <span class="admin-eyebrow">USER MANAGEMENT</span>
            <h2>用户管理</h2>
            <p>禁用账号会阻止登录和接口访问；重置密码不会影响该用户已有数据。</p>
          </div>
          <div class="admin-search">
            <input
              v-model="searchKeyword"
              class="input"
              type="search"
              placeholder="搜索用户名"
              @keyup.enter="loadUsers"
            />
            <button class="btn btn-primary" :disabled="loading" @click="loadUsers">搜索</button>
          </div>
        </div>

        <div v-if="feedbackText" class="admin-feedback" :class="feedbackType">
          {{ feedbackText }}
        </div>

        <div class="admin-table-shell">
          <table class="data-table admin-table">
            <thead>
              <tr>
                <th>用户</th>
                <th>角色</th>
                <th>状态</th>
                <th>注册时间</th>
                <th>最近登录</th>
                <th>账号操作</th>
                <th>密码重置</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!users.length">
                <td colspan="7" class="admin-empty">
                  {{ loading ? "正在加载用户..." : "暂无用户" }}
                </td>
              </tr>
              <tr v-for="user in users" :key="user.id">
                <td>
                  <strong>{{ user.username }}</strong>
                  <span v-if="isSelf(user)" class="admin-self">当前账号</span>
                </td>
                <td>
                  <span class="admin-badge" :class="user.role">
                    {{ user.role === "admin" ? "管理员" : "普通用户" }}
                  </span>
                </td>
                <td>
                  <span class="admin-status" :class="{ disabled: !user.is_active }">
                    {{ user.is_active ? "已启用" : "已禁用" }}
                  </span>
                </td>
                <td>{{ formatDateTime(user.created_at) }}</td>
                <td>{{ formatDateTime(user.last_login_at) }}</td>
                <td>
                  <div class="admin-actions">
                    <button
                      class="btn btn-ghost"
                      :disabled="isSelf(user) || updatingUserId === user.id"
                      @click="toggleUserStatus(user)"
                    >
                      {{ user.is_active ? "禁用" : "启用" }}
                    </button>
                    <button
                      class="btn btn-ghost"
                      :disabled="isSelf(user) || updatingUserId === user.id"
                      @click="toggleUserRole(user)"
                    >
                      {{ user.role === "admin" ? "设为普通用户" : "设为管理员" }}
                    </button>
                  </div>
                </td>
                <td>
                  <div class="admin-password">
                    <input
                      v-model="passwordDrafts[user.id]"
                      class="input"
                      type="password"
                      placeholder="至少 6 位"
                      @keyup.enter="resetPassword(user)"
                    />
                    <button
                      class="btn btn-secondary"
                      :disabled="updatingUserId === user.id"
                      @click="resetPassword(user)"
                    >
                      重置
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </div>
</template>

<script src="./scripts/admin-dashboard.js"></script>

<style scoped src="./styles/admin-dashboard.css"></style>
