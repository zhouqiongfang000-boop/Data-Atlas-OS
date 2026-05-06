<template>
  <aside class="left-panel">
    <div class="surface-card panel-card overview-card">
      <div class="panel-overline">Workspace Signal</div>
      <div class="panel-header compact-header">
        <div>
          <div class="panel-title-row">
            <h3 class="section-title">当前工作状态</h3>
            <button
              type="button"
              class="panel-help-trigger"
              :class="{ active: workspace.isPanelHelpOpen('overview') }"
              aria-label="查看当前工作状态说明"
              @click="workspace.togglePanelHelp('overview')"
            >
              !
            </button>
          </div>
          <p class="section-subtitle">一眼看到当前文件、分析节奏和工作重心</p>
        </div>
      </div>
      <div v-if="workspace.isPanelHelpOpen('overview')" class="panel-help-box">
        <strong>{{ workspace.panelHelpContent.overview.title }}</strong>
        <span>{{ workspace.panelHelpContent.overview.body }}</span>
      </div>

      <div class="overview-list">
        <div class="overview-item">
          <span>当前文件</span>
          <strong class="truncate-text">{{ workspace.selectedFileDisplay || "尚未选择数据文件" }}</strong>
        </div>
        <div class="overview-item">
          <span>图表分析</span>
          <strong>{{ workspace.currentColumn || "等待选择字段" }}</strong>
        </div>
        <div class="overview-item">
          <span>图表类型</span>
          <strong>{{ workspace.currentChartTypeLabel }}</strong>
        </div>
      </div>
    </div>

    <div class="surface-card panel-card upload-card">
      <div class="panel-overline">Input Layer</div>
      <div class="panel-header compact-header">
        <div>
          <div class="panel-title-row">
            <h3 class="section-title">上传数据文件</h3>
            <button
              type="button"
              class="panel-help-trigger"
              :class="{ active: workspace.isPanelHelpOpen('upload') }"
              aria-label="查看上传数据文件说明"
              @click="workspace.togglePanelHelp('upload')"
            >
              !
            </button>
          </div>
          <p class="section-subtitle">继续使用 CSV 作为统一入口，保持流程简单稳定</p>
        </div>
      </div>
      <div v-if="workspace.isPanelHelpOpen('upload')" class="panel-help-box">
        <strong>{{ workspace.panelHelpContent.upload.title }}</strong>
        <span>{{ workspace.panelHelpContent.upload.body }}</span>
      </div>

      <label class="upload-dropzone">
        <input type="file" accept=".csv" @change="workspace.handleUpload" />
        <div class="upload-icon">+</div>
        <strong>拖拽或点击上传 CSV 文件</strong>
        <span>上传后会自动进入文件列表，并可继续预览和分析</span>
      </label>

      <div v-if="workspace.feedbackText" class="feedback-box" :class="workspace.feedbackType">
        {{ workspace.feedbackText }}
      </div>
    </div>

    <div class="surface-card panel-card file-card">
      <div class="panel-overline">File Library</div>
      <div class="panel-header compact-header">
        <div>
          <div class="panel-title-row">
            <h3 class="section-title">文件列表</h3>
            <button
              type="button"
              class="panel-help-trigger"
              :class="{ active: workspace.isPanelHelpOpen('files') }"
              aria-label="查看文件列表说明"
              @click="workspace.togglePanelHelp('files')"
            >
              !
            </button>
          </div>
          <p class="section-subtitle">切换数据源后，右侧工作区会同步更新</p>
        </div>
        <span class="badge badge-primary">{{ workspace.files.length }} 个文件</span>
      </div>
      <div v-if="workspace.isPanelHelpOpen('files')" class="panel-help-box">
        <strong>{{ workspace.panelHelpContent.files.title }}</strong>
        <span>{{ workspace.panelHelpContent.files.body }}</span>
      </div>

      <div v-if="workspace.loadingFiles" class="empty-state">
        <strong>文件加载中</strong>
        <span>正在获取你的数据文件列表...</span>
      </div>

      <div v-else-if="workspace.files.length === 0" class="empty-state">
        <strong>工作区还没有文件</strong>
        <span>先上传一个 CSV 文件，开始你的分析流程</span>
      </div>

      <div v-else class="file-list">
        <div
          v-for="file in workspace.files"
          :key="file.name"
          class="file-item"
          :class="{ active: workspace.selectedFile === file.name }"
        >
          <button class="file-main" @click="workspace.selectFile(file.name)">
            <div class="file-item-top">
              <strong>{{ workspace.formatDisplayName(file.name) }}</strong>
              <span>{{ workspace.formatFileSize(file.size) }}</span>
            </div>
            <div class="file-item-bottom">点击切换到这个数据文件，并刷新预览、统计和图表</div>
          </button>

          <button class="file-delete-btn" @click="workspace.deleteFile(file.name)">删除</button>
        </div>
      </div>
    </div>

    <div class="surface-card panel-card plan-card">
      <div class="panel-overline">Analysis Plans</div>
      <div class="panel-header compact-header">
        <div>
          <div class="panel-title-row">
            <h3 class="section-title">分析方案</h3>
            <button
              type="button"
              class="panel-help-trigger"
              :class="{ active: workspace.isPanelHelpOpen('plans') }"
              aria-label="查看分析方案说明"
              @click="workspace.togglePanelHelp('plans')"
            >
              !
            </button>
          </div>
          <p class="section-subtitle">保存当前文件下的筛选、分组、分布、热力图和图表配置</p>
        </div>
        <span class="badge badge-primary">{{ workspace.analysisPlans.length }} 套</span>
      </div>
      <div v-if="workspace.isPanelHelpOpen('plans')" class="panel-help-box">
        <strong>{{ workspace.panelHelpContent.plans.title }}</strong>
        <span>{{ workspace.panelHelpContent.plans.body }}</span>
      </div>

      <div class="plan-save-form">
        <label class="inline-field">
          <span>方案名称</span>
          <input
            v-model="workspace.planForm.name"
            type="text"
            maxlength="100"
            placeholder="例如：华东销售筛选方案"
          />
        </label>
        <button
          type="button"
          class="btn btn-primary"
          :disabled="!workspace.selectedFile || workspace.savingPlan"
          @click="workspace.saveAnalysisPlan"
        >
          {{ workspace.savingPlan ? "保存中..." : "保存当前方案" }}
        </button>
      </div>

      <div class="groupby-note subtle">
        <strong>同名方案会自动更新</strong>
        <span>恢复方案时，会一起带回当前文件下的查询、分组、分布、相关性和图表设置。</span>
      </div>

      <div v-if="workspace.loadingPlans" class="empty-state compact-empty">
        <strong>方案加载中</strong>
        <span>正在同步当前文件的分析方案...</span>
      </div>

      <div v-else-if="!workspace.selectedFile" class="empty-state compact-empty">
        <strong>先选择文件</strong>
        <span>选定数据文件后，才能保存或恢复这个文件的分析方案。</span>
      </div>

      <div v-else-if="workspace.analysisPlans.length" class="plan-list">
        <div
          v-for="plan in workspace.analysisPlans"
          :key="plan.id"
          class="plan-item"
        >
          <div class="plan-item-head">
            <strong>{{ plan.name }}</strong>
            <span>{{ workspace.formatDateTime(plan.updated_at || plan.created_at) }}</span>
          </div>

          <div class="plan-meta">
            <span class="badge badge-soft">
              {{ plan.summary?.query_filter_count || 0 }} 条筛选
            </span>
            <span class="badge badge-soft">
              {{ plan.summary?.group_column_count || 0 }} 个分组字段
            </span>
            <span class="badge badge-soft">
              {{ plan.summary?.group_metric_count || 0 }} 个统计项
            </span>
            <span v-if="plan.summary?.distribution_column" class="badge badge-soft">
              分布：{{ plan.summary.distribution_column }}
            </span>
            <span v-if="plan.summary?.chart_column" class="badge badge-soft">
              图表：{{ plan.summary.chart_column }}
            </span>
          </div>

          <div class="plan-actions">
            <button
              type="button"
              class="btn btn-ghost"
              :disabled="workspace.applyingPlanId === plan.id"
              @click="workspace.applyAnalysisPlan(plan)"
            >
              {{ workspace.applyingPlanId === plan.id ? "恢复中..." : "恢复方案" }}
            </button>
            <button
              type="button"
              class="btn btn-danger-soft"
              :disabled="workspace.deletingPlanId === plan.id"
              @click="workspace.deleteAnalysisPlan(plan.id)"
            >
              {{ workspace.deletingPlanId === plan.id ? "删除中..." : "删除" }}
            </button>
          </div>
        </div>
      </div>

      <div v-else class="empty-state compact-empty">
        <strong>还没有分析方案</strong>
        <span>把当前分析配置存成方案后，下次可以一键恢复继续分析。</span>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { inject } from "vue";

const workspace = inject("workspaceCtx");
</script>
