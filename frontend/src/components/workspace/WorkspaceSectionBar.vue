<template>
  <section class="workspace-section-bar surface-card">
    <div class="workspace-section-copy">
      <span class="panel-overline">Workflow Navigation</span>
      <h2>按工作流切换模块，不再整页向下翻找功能</h2>
      <p>左侧保留文件与方案入口，右侧只展示当前阶段最需要的工具，后续图片工作流也能沿用这套结构。</p>
    </div>
    <div class="workspace-section-pills">
      <button
        v-for="option in workspace.WORKSPACE_SECTION_OPTIONS"
        :key="option.value"
        type="button"
        class="workspace-section-pill"
        :class="{ active: workspace.activeWorkspaceSection === option.value }"
        @click="workspace.setWorkspaceSection(option.value)"
      >
        <span>{{ option.label }}</span>
        <small>{{ option.description }}</small>
      </button>
    </div>
  </section>
</template>

<script setup>
import { inject } from "vue";

const workspace = inject("workspaceCtx");
</script>
