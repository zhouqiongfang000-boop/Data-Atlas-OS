<template>
  <section v-show="workspace.activeWorkspaceSection === 'assets'" class="workspace-section-panel">
    <div class="surface-card panel-card ai-assistant-summary-card">
      <div class="panel-overline">AI Assistant Center</div>
      <div class="panel-header">
        <div>
          <div class="panel-title-row">
            <h3 class="section-title">AI 助手中心</h3>
            <button
              type="button"
              class="panel-help-trigger"
              :class="{ active: workspace.isPanelHelpOpen('assistant') }"
              aria-label="查看 AI 分析助手说明"
              @click="workspace.togglePanelHelp('assistant')"
            >
              !
            </button>
          </div>
          <p class="section-subtitle">这里显示 AI 助手的当前状态、最近一次结论和快捷入口；完整对话可以在全局助手抽屉里继续。</p>
        </div>
        <div class="ai-status-stack">
          <span class="badge" :class="aiStatusBadgeClass">{{ aiStatusLabel }}</span>
          <span v-if="workspace.aiStatus.provider" class="badge badge-primary">{{ aiProviderLabel }}</span>
          <span v-if="workspace.aiStatus.model" class="badge badge-primary">{{ workspace.aiStatus.model }}</span>
        </div>
      </div>

      <div v-if="workspace.isPanelHelpOpen('assistant')" class="panel-help-box">
        <strong>{{ workspace.panelHelpContent.assistant.title }}</strong>
        <span>{{ workspace.panelHelpContent.assistant.body }}</span>
      </div>

      <div class="ai-status-card" :class="{ unavailable: !workspace.aiStatus.enabled }">
        <div>
          <strong>{{ aiStatusHeadline }}</strong>
          <p>{{ aiStatusDescription }}</p>
        </div>
        <div class="ai-status-meta">
          <span v-if="workspace.selectedFileDisplay" class="badge badge-success truncate-text">
            当前文件：{{ workspace.selectedFileDisplay }}
          </span>
          <span v-if="workspace.aiAssistantLastCompletedAt" class="badge badge-soft">
            最近分析：{{ formattedAiCompletedAt }}
          </span>
        </div>
      </div>

      <div class="ai-prompt-strip">
        <button
          v-for="prompt in workspace.aiContextualPrompts"
          :key="prompt"
          type="button"
          class="field-chip"
          :disabled="workspace.loadingAiAssistant || !workspace.aiStatus.enabled"
          @click="workspace.openAiAssistantDrawer(prompt)"
        >
          {{ prompt }}
        </button>
      </div>

      <div class="ai-summary-actions">
        <button
          type="button"
          class="btn btn-ghost"
          :disabled="!workspace.aiStatus.enabled || workspace.loadingAiAssistant"
          @click="workspace.explainCurrentAnalysisResult"
        >
          解释当前结果
        </button>
        <button
          type="button"
          class="btn btn-primary"
          :disabled="!workspace.aiStatus.enabled"
          @click="workspace.openAiAssistantDrawer()"
        >
          打开 AI 助手
        </button>
        <button
          type="button"
          class="btn btn-ghost"
          :disabled="!workspace.aiStatus.enabled || !workspace.selectedFile"
          @click="workspace.generateAiPresentationSummary"
        >
          生成展示摘要
        </button>
      </div>

      <div v-if="workspace.latestAiAssistantMessage" class="ai-latest-brief">
        <div class="ai-latest-brief__head">
          <div class="ai-latest-brief__title">
            <strong>最近一次 AI 结论</strong>
            <span v-if="workspace.latestAiAssistantMessage.modeLabel" class="badge badge-soft">
              {{ workspace.latestAiAssistantMessage.modeLabel }}
            </span>
          </div>
          <div class="ai-latest-brief__actions">
            <span v-if="workspace.latestAiAssistantMessage.provider || workspace.latestAiAssistantMessage.model">
              {{ workspace.latestAiAssistantMessage.provider || "AI" }} · {{ workspace.latestAiAssistantMessage.model || "default" }}
            </span>
            <button
              type="button"
              class="btn btn-ghost ai-copy-btn"
              @click="workspace.copyAiMessageContent(workspace.latestAiAssistantMessage)"
            >
              复制
            </button>
          </div>
        </div>
        <p>{{ workspace.latestAiAssistantMessage.content }}</p>
      </div>

      <div v-else class="empty-state compact-empty">
        <strong>还没有 AI 结论</strong>
        <span>点击上面的快捷问题或“打开 AI 助手”，就能从任何模块继续对话。</span>
      </div>

      <div v-if="workspace.latestAiPresentationMessage" class="ai-latest-brief ai-presentation-brief">
        <div class="ai-latest-brief__head">
          <div class="ai-latest-brief__title">
            <strong>最近一次展示摘要</strong>
            <span class="badge badge-soft">展示摘要</span>
          </div>
          <div class="ai-latest-brief__actions">
            <button
              type="button"
              class="btn btn-ghost ai-copy-btn"
              @click="workspace.copyAiMessageContent(workspace.latestAiPresentationMessage)"
            >
              复制摘要
            </button>
          </div>
        </div>
        <p>{{ workspace.latestAiPresentationMessage.content }}</p>
      </div>
    </div>

    <div class="surface-card panel-card history-card">
      <div class="panel-overline">Recent Output</div>
      <div class="panel-header">
        <div>
          <div class="panel-title-row">
            <h3 class="section-title">最近分析记录</h3>
            <button
              type="button"
              class="panel-help-trigger"
              :class="{ active: workspace.isPanelHelpOpen('history') }"
              aria-label="查看最近分析记录说明"
              @click="workspace.togglePanelHelp('history')"
            >
              !
            </button>
          </div>
          <p class="section-subtitle">记录你最近生成过的图表分析，方便回看展示路径</p>
        </div>
        <span class="badge badge-primary">{{ workspace.historyRecords.length }} 条</span>
      </div>
      <div v-if="workspace.isPanelHelpOpen('history')" class="panel-help-box">
        <strong>{{ workspace.panelHelpContent.history.title }}</strong>
        <span>{{ workspace.panelHelpContent.history.body }}</span>
      </div>

      <div v-if="workspace.historyRecords.length" class="table-shell">
        <table class="data-table">
          <thead>
            <tr>
              <th>文件名</th>
              <th>字段</th>
              <th>图表类型</th>
              <th>时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in workspace.historyRecords" :key="item.id">
              <td>{{ item.file_name }}</td>
              <td>{{ item.column_name }}</td>
              <td>{{ item.chart_type }}</td>
              <td>{{ workspace.formatDateTime(item.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else class="empty-state">
        <strong>暂无分析记录</strong>
        <span>生成图表后会自动记录在这里，方便你回顾展示轨迹。</span>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, inject } from "vue";

const workspace = inject("workspaceCtx");

const aiProviderLabel = computed(() => {
  const provider = workspace.aiStatus?.provider || "";
  if (provider === "alibaba") return "阿里云百炼";
  if (provider === "openai_compatible") return "兼容接口";
  return provider || "未配置";
});

const aiStatusLabel = computed(() => (workspace.aiStatus?.enabled ? "已连接" : "待配置"));

const aiStatusBadgeClass = computed(() =>
  workspace.aiStatus?.enabled ? "badge-success" : "badge-warning"
);

const aiStatusHeadline = computed(() => {
  if (!workspace.aiStatus?.enabled) return "AI 助手暂未就绪";
  if (!workspace.selectedFile) return "AI 已就绪，等待你选择数据文件";
  if (workspace.loadingAiAssistant) return "AI 正在整理本次分析建议";
  return "AI 已就绪，可以从任何模块继续提问";
});

const aiStatusDescription = computed(() => {
  if (!workspace.aiStatus?.enabled) {
    return "请在后端环境变量里设置 AI_PROVIDER、DASHSCOPE_API_KEY（或 AI_API_KEY）和 AI_MODEL，然后刷新页面。";
  }
  if (!workspace.selectedFile) {
    return "选择文件后，AI 会结合字段画像、质量报告和基础统计结果，给你更贴近当前数据的建议。";
  }
  if (workspace.loadingAiAssistant) {
    return "首次调用或上下文较大时，AI 可能需要 10 到 60 秒，请耐心等待。";
  }
  return "建议把 AI 当成分析工作流助手：让它解释结果、推荐下一步，而不是替代系统做真实统计计算。";
});

const formattedAiCompletedAt = computed(() => {
  if (!workspace.aiAssistantLastCompletedAt) return "";
  return workspace.formatDateTime(workspace.aiAssistantLastCompletedAt);
});
</script>
