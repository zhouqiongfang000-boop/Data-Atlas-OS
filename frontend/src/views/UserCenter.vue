<template>
  <div class="user-center page-enter">
    <main class="app-shell user-center__shell">
      <section class="account-hero">
        <article class="account-identity" aria-label="账户概览">
          <span class="user-eyebrow">ACCOUNT CENTER</span>
          <h1>{{ currentUser.username || "个人中心" }}</h1>
          <p>账号信息、安全设置、数据分析记录和图片处理历史，现在统一收在个人中心。</p>

          <dl class="account-meta">
            <div>
              <dt>身份</dt>
              <dd>
                <span class="user-role" :class="currentUser.role">
                  {{ currentUser.role === "admin" ? "管理员" : "普通用户" }}
                </span>
              </dd>
            </div>
            <div>
              <dt>账号状态</dt>
              <dd>{{ currentUser.is_active ? "已启用" : "已禁用" }}</dd>
            </div>
            <div>
              <dt>注册时间</dt>
              <dd>{{ formatDateTime(currentUser.created_at) }}</dd>
            </div>
            <div>
              <dt>最近登录</dt>
              <dd>{{ formatDateTime(currentUser.last_login_at) }}</dd>
            </div>
          </dl>

          <nav class="account-actions" aria-label="工作台快捷入口">
            <button type="button" class="btn btn-primary" @click="openDataWorkspace">
              数据工作台
            </button>
            <button type="button" class="btn btn-ghost" @click="openImageWorkspace">
              图片工作台
            </button>
          </nav>
        </article>

        <form class="security-panel" @submit.prevent="changePassword">
          <span class="user-eyebrow">SECURITY</span>
          <h2>修改密码</h2>
          <p>建议使用至少 6 位且不容易被猜到的新密码。</p>

          <label class="form-group">
            <span class="form-label">旧密码</span>
            <input v-model="passwordForm.old_password" class="input" type="password" />
          </label>
          <label class="form-group">
            <span class="form-label">新密码</span>
            <input v-model="passwordForm.new_password" class="input" type="password" />
          </label>

          <button class="btn btn-primary" :disabled="savingPassword" type="submit">
            {{ savingPassword ? "更新中..." : "更新密码" }}
          </button>

          <p v-if="feedbackText" class="user-feedback" :class="feedbackType">
            {{ feedbackText }}
          </p>
        </form>
      </section>

      <section class="user-metrics" aria-label="我的工作区统计">
        <article v-for="metric in workspaceMetrics" :key="metric.key" class="metric-tile">
          <span>{{ metric.label }}</span>
          <strong>{{ metric.value }}</strong>
          <small>{{ metric.helper }}</small>
        </article>
      </section>

      <section class="activity-layout">
        <article class="user-panel activity-chart-panel">
          <header class="panel-heading">
            <div>
              <span class="user-eyebrow">USAGE FREQUENCY</span>
              <h2>近 14 天使用频率</h2>
            </div>
            <strong>{{ totalRecentActivity }} 次</strong>
          </header>
          <div class="activity-chart-wrap">
            <div ref="activityChartRef" class="activity-chart" aria-label="使用频率图表"></div>
            <p v-if="!loading && !totalRecentActivity" class="chart-empty">
              暂无可统计的使用记录
            </p>
          </div>
        </article>

        <aside class="user-panel activity-digest" aria-label="活跃度摘要">
          <span class="user-eyebrow">ACTIVITY SIGNAL</span>
          <h2>使用概览</h2>
          <dl>
            <div>
              <dt>最近活动</dt>
              <dd>{{ latestActivityTime }}</dd>
            </div>
            <div>
              <dt>最活跃日期</dt>
              <dd>{{ busiestDayLabel }}</dd>
            </div>
            <div>
              <dt>统一历史</dt>
              <dd>{{ combinedActivities.length }} 条</dd>
            </div>
          </dl>
        </aside>
      </section>

      <section class="user-panel unified-history">
        <header class="panel-heading">
          <div>
            <span class="user-eyebrow">UNIFIED HISTORY</span>
            <h2>最近分析与图片处理</h2>
          </div>
          <div class="history-filters" aria-label="历史筛选">
            <button
              type="button"
              :class="{ active: historyFilter === 'all' }"
              @click="historyFilter = 'all'"
            >
              全部
            </button>
            <button
              type="button"
              :class="{ active: historyFilter === 'analysis' }"
              @click="historyFilter = 'analysis'"
            >
              数据分析
            </button>
            <button
              type="button"
              :class="{ active: historyFilter === 'image' }"
              @click="historyFilter = 'image'"
            >
              图片处理
            </button>
          </div>
        </header>

        <p v-if="loading" class="history-empty">正在同步个人历史...</p>
        <ol v-else-if="filteredActivities.length" class="history-list">
          <li
            v-for="item in filteredActivities"
            :key="item.id"
            class="history-item"
            :class="`history-item--${item.kind}`"
          >
            <span class="history-type">{{ item.label }}</span>
            <strong>{{ item.title }}</strong>
            <time>{{ formatDateTime(item.created_at) }}</time>
            <p>{{ item.detail }}</p>
          </li>
        </ol>
        <p v-else class="history-empty">暂无对应历史记录</p>
      </section>
    </main>
  </div>
</template>

<script src="./scripts/user-center.js"></script>

<style scoped src="./styles/user-center.css"></style>
