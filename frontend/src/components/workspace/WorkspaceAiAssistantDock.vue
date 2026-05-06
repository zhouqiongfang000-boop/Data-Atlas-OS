<template>
  <Teleport to="body">
    <div class="ai-dock-root">
    <transition name="ai-dock-fade">
      <div
        v-if="workspace.showAiAssistantDrawer"
        class="ai-dock-overlay"
        @click="workspace.closeAiAssistantDrawer"
      ></div>
    </transition>

    <button
      v-if="!workspace.showAiAssistantDrawer"
      type="button"
      class="ai-dock-launcher"
      :class="{ busy: workspace.loadingAiAssistant }"
      @click="workspace.openAiAssistantDrawer()"
    >
      <span class="ai-dock-launcher__label">AI 助手</span>
      <small>{{ launcherText }}</small>
    </button>

    <aside v-if="workspace.showAiAssistantDrawer" class="ai-dock-panel glass-card">
      <header class="ai-dock-panel__header">
        <div>
          <span class="panel-overline">AI Copilot</span>
          <h3>数据分析助手</h3>
          <p>{{ currentSectionLabel }}下也能直接提问，不用切回资产中心。</p>
        </div>

        <div class="ai-dock-panel__actions">
          <span class="badge" :class="aiStatusBadgeClass">{{ aiStatusLabel }}</span>
          <button
            type="button"
            class="panel-help-trigger"
            aria-label="关闭 AI 助手"
            @click="workspace.closeAiAssistantDrawer"
          >
            ×
          </button>
        </div>
      </header>

      <div class="ai-dock-status">
        <div>
          <strong>{{ aiStageTitle }}</strong>
          <p>{{ aiStageDescription }}</p>
        </div>
        <div class="ai-status-stack">
          <span v-if="workspace.aiStatus.provider" class="badge badge-primary">{{ aiProviderLabel }}</span>
          <span v-if="workspace.aiStatus.model" class="badge badge-primary">{{ workspace.aiStatus.model }}</span>
        </div>
      </div>

      <div class="ai-dock-stage-strip">
        <span class="badge" :class="{ 'badge-success': stageReached('context'), 'badge-soft': !stageReached('context') }">
          读取上下文
        </span>
        <span class="badge" :class="{ 'badge-success': stageReached('model'), 'badge-soft': !stageReached('model') }">
          调用模型
        </span>
        <span class="badge" :class="{ 'badge-success': stageReached('compose'), 'badge-soft': !stageReached('compose') }">
          整理建议
        </span>
      </div>

      <div class="ai-prompt-strip ai-dock-prompts">
        <button
          v-for="prompt in workspace.aiContextualPrompts"
          :key="prompt"
          type="button"
          class="field-chip"
          :disabled="workspace.loadingAiAssistant || !workspace.aiStatus.enabled"
          @click="workspace.fillAiQuestion(prompt)"
        >
          {{ prompt }}
        </button>
      </div>

      <label class="inline-field ai-composer-field">
        <span>提问内容</span>
        <textarea
          v-model="workspace.aiAssistantForm.question"
          rows="4"
          placeholder="例如：帮我解释这张图表为什么值得展示，或者推荐我下一步最有价值的分析。"
          :disabled="workspace.loadingAiAssistant || !workspace.aiStatus.enabled"
          @keydown.ctrl.enter.prevent="workspace.askAiAssistant()"
        />
      </label>

      <div v-if="workspace.aiAssistantLastError" class="ai-error-banner">
        <strong>本次调用提示</strong>
        <span>{{ workspace.aiAssistantLastError }}</span>
      </div>

      <div class="ai-dock-toolbar">
        <div class="groupby-note subtle ai-dock-tip">
          <strong>使用建议</strong>
          <span>问得越具体，AI 给出的建议越稳。首次分析或上下文较大时，可能需要等待 10 到 60 秒。</span>
        </div>

        <div class="ai-composer-actions">
          <button
            type="button"
            class="btn btn-ghost"
            :disabled="workspace.loadingAiAssistant || !workspace.aiStatus.enabled"
            @click="workspace.explainCurrentAnalysisResult"
          >
            解释当前结果
          </button>
          <button
            type="button"
            class="btn btn-ghost"
            :disabled="workspace.loadingAiAssistant || !workspace.aiStatus.enabled"
            @click="workspace.generateAiPresentationSummary"
          >
            展示摘要
          </button>
          <button
            type="button"
            class="btn btn-ghost"
            :disabled="workspace.loadingAiAssistant || !workspace.aiAssistantMessages.length"
            @click="workspace.clearAiConversation"
          >
            清空对话
          </button>
          <button
            type="button"
            class="btn btn-primary"
            :disabled="workspace.loadingAiAssistant || !workspace.aiStatus.enabled"
            @click="workspace.askAiAssistant()"
          >
            {{ workspace.loadingAiAssistant ? "分析中..." : "发送给 AI" }}
          </button>
        </div>
      </div>

      <div v-if="!workspace.selectedFile" class="empty-state compact-empty">
        <strong>先选择一个数据文件</strong>
        <span>AI 会围绕当前文件的字段结构、质量报告和已有分析结果回答问题，所以需要先选中文件。</span>
      </div>

      <div v-else-if="workspace.aiAssistantMessages.length" class="ai-conversation-list ai-dock-conversation">
        <article
          v-for="(message, index) in workspace.aiAssistantMessages"
          :key="`${message.role}-${index}`"
          class="ai-message-card"
          :class="`role-${message.role}`"
        >
          <div class="ai-message-head">
            <div class="ai-message-head__main">
              <strong>{{ message.role === "user" ? "你" : "AI 助手" }}</strong>
              <span v-if="message.modeLabel" class="badge badge-soft">{{ message.modeLabel }}</span>
            </div>
            <div class="ai-message-head__side">
              <span v-if="message.role === 'assistant' && (message.provider || message.model)">
                {{ message.provider || "AI" }} · {{ message.model || "default" }}
              </span>
              <button
                v-if="message.role === 'assistant' && message.content"
                type="button"
                class="btn btn-ghost ai-copy-btn"
                @click="workspace.copyAiMessageContent(message)"
              >
                复制
              </button>
            </div>
          </div>

          <p class="ai-message-content">{{ message.content }}</p>

          <div
            v-if="message.role === 'assistant' && Array.isArray(message.insights) && message.insights.length"
            class="ai-message-block"
          >
            <strong>关键发现</strong>
            <ul class="ai-message-list">
              <li v-for="(item, insightIndex) in message.insights" :key="`insight-${insightIndex}`">
                {{ item }}
              </li>
            </ul>
          </div>

          <div
            v-if="message.role === 'assistant' && Array.isArray(message.cautions) && message.cautions.length"
            class="ai-message-block caution"
          >
            <strong>风险提醒</strong>
            <ul class="ai-message-list">
              <li v-for="(item, cautionIndex) in message.cautions" :key="`caution-${cautionIndex}`">
                {{ item }}
              </li>
            </ul>
          </div>

          <div
            v-if="
              message.role === 'assistant' &&
              Array.isArray(message.suggestedActions) &&
              message.suggestedActions.length
            "
            class="ai-message-block"
          >
            <strong>建议下一步</strong>
            <div class="ai-action-list">
              <button
                v-for="(action, actionIndex) in message.suggestedActions"
                :key="`action-${actionIndex}`"
                type="button"
                class="btn btn-ghost ai-action-btn"
                @click="workspace.applyAiSuggestedAction(action)"
              >
                <span>{{ action.label }}</span>
                <small>{{ action.description }}</small>
              </button>
            </div>
          </div>
        </article>
      </div>

      <div v-else class="empty-state compact-empty">
        <strong>还没有 AI 对话</strong>
        <span>你可以先点上面的快捷问题，或者直接输入一个分析问题发给 AI。</span>
      </div>
    </aside>
    </div>
  </Teleport>
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

const aiStatusLabel = computed(() => {
  if (workspace.loadingAiAssistant) return "分析中";
  return workspace.aiStatus?.enabled ? "已连接" : "待配置";
});

const aiStatusBadgeClass = computed(() => {
  if (workspace.loadingAiAssistant) return "badge-primary";
  return workspace.aiStatus?.enabled ? "badge-success" : "badge-warning";
});

const currentSectionLabel = computed(() => {
  const option = (workspace.WORKSPACE_SECTION_OPTIONS || []).find(
    (item) => item.value === workspace.activeWorkspaceSection
  );
  return option?.label || "当前模块";
});

const launcherText = computed(() => {
  if (workspace.loadingAiAssistant) return "分析中";
  if (!workspace.aiStatus?.enabled) return "待配置";
  return "随时提问";
});

const aiStageTitle = computed(() => {
  if (!workspace.aiStatus?.enabled) return "AI 助手暂未就绪";
  if (workspace.aiAssistantStage === "context") return "正在读取当前文件上下文";
  if (workspace.aiAssistantStage === "model") return "正在调用 AI 模型";
  if (workspace.aiAssistantStage === "compose") return "正在整理分析建议";
  if (workspace.aiAssistantStage === "error") return "本次分析未成功完成";
  if (workspace.aiAssistantStage === "done") return "AI 已返回本次建议";
  return "AI 已就绪，可以开始提问";
});

const aiStageDescription = computed(() => {
  if (!workspace.aiStatus?.enabled) {
    return "请先在后端环境变量中配置模型提供商、API Key 和模型名称。";
  }
  if (workspace.aiAssistantStage === "error") {
    return workspace.aiAssistantLastError || "本次分析未能正常返回结果，你可以稍后重试。";
  }
  if (workspace.loadingAiAssistant) {
    return "首次分析或上下文较大时，AI 可能需要等待 10 到 60 秒。";
  }
  return "AI 会参考当前文件的字段画像、质量检查和基础分析结果，尽量给出可执行的建议。";
});

const stageReached = (stage) => {
  const order = ["idle", "context", "model", "compose", "done"];
  const currentIndex = order.indexOf(workspace.aiAssistantStage || "idle");
  const targetIndex = order.indexOf(stage);
  if (workspace.aiAssistantStage === "error") {
    return stage === "context" || stage === "model";
  }
  return currentIndex >= targetIndex && targetIndex > 0;
};
</script>
