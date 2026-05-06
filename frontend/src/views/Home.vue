<template>
  <div ref="homeRoot" class="os-home page-enter">
    <section class="os-hero">
      <div class="os-hero__copy" data-home-animate>
        <span class="os-eyebrow">DATA ATLAS OS</span>
        <h1>
          <span>像打开一台</span>
          <span>智能工作电脑</span>
        </h1>
        <p>
          数据、图像、管理，一站式连接。把上传、清洗、统计、图表、图像增强和账号资产整合为一个轻盈的 OS 工作流首页。
        </p>

        <div class="os-hero__actions">
          <button class="os-button os-button--primary" type="button" @click="openDataWorkspace('overview')">
            <NIcon><AnalyticsOutline /></NIcon>
            开始使用
          </button>
          <button class="os-button os-button--glass" type="button" @click="scrollToWorkflow">
            <NIcon><LayersOutline /></NIcon>
            查看工作流
          </button>
        </div>

        <div class="os-status-row" aria-label="平台能力">
          <span v-for="chip in featureChips" :key="chip">{{ chip }}</span>
        </div>
      </div>

      <div class="os-floating-stage" data-home-animate aria-label="平台能力预览">
        <article class="float-panel float-panel--main">
          <header>
            <span>实时趋势</span>
            <strong>Workspace Pulse</strong>
          </header>
          <div class="float-metrics">
            <div>
              <strong>{{ dashboardSummary.file_count || files.length }}</strong>
              <span>数据文件</span>
            </div>
            <div>
              <strong>{{ images.length }}</strong>
              <span>图片资产</span>
            </div>
            <div>
              <strong>{{ workspaceReadiness }}%</strong>
              <span>完整度</span>
            </div>
          </div>
          <svg class="trend-chart" viewBox="0 0 320 130" role="img" aria-label="数据趋势图">
            <defs>
              <linearGradient id="trendFill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="#0a84ff" stop-opacity="0.24" />
                <stop offset="100%" stop-color="#0a84ff" stop-opacity="0" />
              </linearGradient>
            </defs>
            <path class="trend-area" d="M0,104 C40,86 58,92 88,70 C126,42 146,66 178,48 C214,28 236,44 264,30 C286,20 302,24 320,16 L320,130 L0,130 Z" />
            <path class="trend-line" d="M0,104 C40,86 58,92 88,70 C126,42 146,66 178,48 C214,28 236,44 264,30 C286,20 302,24 320,16" />
          </svg>
        </article>

        <article class="float-panel float-panel--image">
          <span class="panel-icon">
            <NIcon><ImagesOutline /></NIcon>
          </span>
          <strong>图片工作台</strong>
          <p>AI 修复、批量增强、图片分类</p>
        </article>

        <article class="float-panel float-panel--account">
          <span class="panel-icon panel-icon--violet">
            <NIcon><PersonCircleOutline /></NIcon>
          </span>
          <strong>{{ currentUser?.username || "个人中心" }}</strong>
          <p>{{ files.length }} 项目 · {{ images.length }} 图片 · {{ historyRecords.length }} 任务</p>
        </article>
      </div>
    </section>

    <section ref="workflowSection" class="os-workflows" aria-label="工作流入口">
      <article
        v-for="workflow in workflowCards"
        :key="workflow.key"
        class="workflow-card"
        data-home-animate
        @click="workflow.action"
      >
        <div class="workflow-card__icon">
          <NIcon>
            <component :is="workflow.icon" />
          </NIcon>
        </div>
        <span class="os-eyebrow">{{ workflow.kicker }}</span>
        <h2>{{ workflow.title }}</h2>
        <p>{{ workflow.description }}</p>
        <div class="workflow-steps">
          <span v-for="step in workflow.steps" :key="step">{{ step }}</span>
        </div>
      </article>
    </section>
  </div>
</template>

<script src="./scripts/dashboard-home.js"></script>

<style src="./styles/dashboard-home.css"></style>
