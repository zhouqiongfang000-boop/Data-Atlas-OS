<template>
  <div class="dashboard-page data-workspace page-enter">
    <div class="dashboard-mesh"></div>
    <div class="dashboard-glow glow-a"></div>
    <div class="dashboard-glow glow-b"></div>

    <div class="app-shell dashboard-shell">
      <header class="command-header">
        <div class="command-brand">
          <div class="command-mark" aria-hidden="true">
            <span class="command-mark-square"></span>
            <span class="command-mark-core">DA</span>
          </div>

          <div class="command-copy">
            <div class="command-kicker">DATA ATLAS COMMAND DECK</div>
            <h1 class="command-title">数据分析工作台</h1>
            <p class="command-desc">
              把上传、预览、清洗、查询、分组、图表和相关性整合到同一个工作台里，但不再通过一条超长页面承载所有内容。
            </p>
          </div>
        </div>

        <div class="command-side">
          <div class="command-user">
            <span class="command-user-label">Current Operator</span>
            <strong>{{ currentUser?.username || "未登录用户" }}</strong>
          </div>

          <div class="topbar-actions">
            <button class="btn btn-ghost" @click="fetchFiles(true)">刷新工作区</button>
          </div>
        </div>
      </header>

      <section class="hero-grid">
        <div class="hero-main">
          <div class="hero-badge">Brand-consistent Workspace</div>
          <h2>从预览到可视化，把分析流程压缩成更短、更清晰的工作流。</h2>
          <p>
            这里保留你现在所有核心数据分析能力，但通过工作流分区切换来减少滚动距离。后续图片工作流也可以沿用这套平台结构，互不挤占。
          </p>

          <div class="hero-ribbon">
            <span>Upload Ready</span>
            <span>Quality First</span>
            <span>Insight Storytelling</span>
            <span>Presentation Friendly</span>
          </div>
        </div>

        <div class="hero-side">
          <div class="surface-card metric-card">
            <span class="metric-label">文件总数</span>
            <strong>{{ files.length }}</strong>
            <p>当前工作区中的数据文件数量。</p>
          </div>

          <div class="surface-card metric-card">
            <span class="metric-label">数值字段</span>
            <strong>{{ analysis?.numeric_columns?.length || 0 }}</strong>
            <p>可直接进入统计、热力图和图表分析的字段。</p>
          </div>

          <div class="surface-card metric-card">
            <span class="metric-label">类别字段</span>
            <strong>{{ analysis?.categorical_columns?.length || 0 }}</strong>
            <p>适合做分布分析、分组统计和构成展示的字段。</p>
          </div>

          <div class="surface-card metric-card">
            <span class="metric-label">最近记录</span>
            <strong>{{ historyRecords.length }}</strong>
            <p>最近生成过的分析记录数量。</p>
          </div>
        </div>
      </section>

      <WorkspaceSectionBar />

      <section class="workspace-grid">
        <div class="workspace-sidebar-column">
          <WorkspaceSidebar />
        </div>

        <main class="right-panel">
          <WorkspaceOverviewSection />
          <WorkspacePreparationSection />
          <WorkspaceExplorationSection />
          <WorkspaceVisualizationSection />
          <WorkspaceAssetsSection />
        </main>
      </section>

      <WorkspaceAiAssistantDock />
    </div>
  </div>
</template>

<script src="./scripts/home.js"></script>

<style src="./styles/home.css"></style>
