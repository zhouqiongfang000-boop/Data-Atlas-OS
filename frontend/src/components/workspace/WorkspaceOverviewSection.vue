<template>
  <section v-show="workspace.activeWorkspaceSection === 'overview'" class="workspace-section-panel">
    <div class="surface-card panel-card preview-card">
      <div class="panel-overline">Dataset Preview</div>
      <div class="panel-header">
        <div>
          <div class="panel-title-row">
            <h3 class="section-title">数据预览</h3>
            <button
              type="button"
              class="panel-help-trigger"
              :class="{ active: workspace.isPanelHelpOpen('preview') }"
              aria-label="查看数据预览说明"
              @click="workspace.togglePanelHelp('preview')"
            >
              !
            </button>
          </div>
          <p class="section-subtitle">快速查看当前文件前 10 行，判断字段结构是否符合预期</p>
        </div>
        <span class="badge badge-success" v-if="workspace.selectedFileDisplay">
          {{ workspace.selectedFileDisplay }}
        </span>
      </div>
      <div v-if="workspace.isPanelHelpOpen('preview')" class="panel-help-box">
        <strong>{{ workspace.panelHelpContent.preview.title }}</strong>
        <span>{{ workspace.panelHelpContent.preview.body }}</span>
      </div>

      <div v-if="workspace.loadingPreview" class="empty-state">
        <strong>预览加载中</strong>
        <span>正在读取当前文件的数据内容...</span>
      </div>

      <div v-else-if="workspace.previewColumns.length" class="table-shell">
        <table class="data-table">
          <thead>
            <tr>
              <th v-for="col in workspace.previewColumns" :key="col">{{ col }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in workspace.previewData" :key="index">
              <td v-for="col in workspace.previewColumns" :key="col">
                {{ row[col] }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else class="empty-state">
        <strong>还没有预览数据</strong>
        <span>先从左侧选择一个文件，再开始查看数据内容</span>
      </div>
    </div>

    <div class="surface-card panel-card dictionary-card">
      <div class="panel-overline">Field Dictionary</div>
      <div class="panel-header">
        <div>
          <div class="panel-title-row">
            <h3 class="section-title">字段画像 / 数据字典</h3>
            <button
              type="button"
              class="panel-help-trigger"
              :class="{ active: workspace.isPanelHelpOpen('dictionary') }"
              aria-label="查看字段画像说明"
              @click="workspace.togglePanelHelp('dictionary')"
            >
              !
            </button>
          </div>
          <p class="section-subtitle">把每个字段是什么、质量如何、适合做什么分析，整理成一眼能看懂的说明层</p>
        </div>
        <span class="badge badge-primary" v-if="workspace.fieldProfileReport">
          {{ workspace.fieldProfileReport.field_count }} 个字段
        </span>
      </div>
      <div v-if="workspace.isPanelHelpOpen('dictionary')" class="panel-help-box">
        <strong>{{ workspace.panelHelpContent.dictionary.title }}</strong>
        <span>{{ workspace.panelHelpContent.dictionary.body }}</span>
      </div>

      <div v-if="workspace.loadingFieldProfiles" class="empty-state">
        <strong>字段画像生成中</strong>
        <span>正在整理字段类型、样本值和推荐分析方向...</span>
      </div>

      <template v-else-if="workspace.fieldProfileReport">
        <div class="dictionary-toolbar">
          <label class="inline-field">
            <span>搜索字段</span>
            <input
              v-model="workspace.fieldDictionaryForm.search"
              type="text"
              placeholder="按字段名、类型或角色提示搜索"
            />
          </label>

          <div class="inline-field">
            <span>按类型查看</span>
            <div class="column-toolbar compact-toolbar">
              <button
                v-for="option in workspace.FIELD_PROFILE_TYPE_OPTIONS"
                :key="option.value"
                type="button"
                class="field-chip"
                :class="{ active: workspace.fieldDictionaryForm.type === option.value }"
                @click="workspace.fieldDictionaryForm.type = option.value"
              >
                {{ option.label }}
                <template v-if="option.value !== 'all'">
                  · {{ workspace.fieldProfileTypeCounts[option.value] || 0 }}
                </template>
              </button>
            </div>
          </div>
        </div>

        <div class="dictionary-summary-bar">
          <span class="badge badge-success">数值 {{ workspace.fieldProfileTypeCounts.numeric || 0 }}</span>
          <span class="badge badge-primary">类别 {{ workspace.fieldProfileTypeCounts.categorical || 0 }}</span>
          <span class="badge badge-primary">日期时间 {{ workspace.fieldProfileTypeCounts.datetime || 0 }}</span>
          <span class="badge badge-primary">空列 {{ workspace.fieldProfileTypeCounts.empty || 0 }}</span>
          <span class="badge badge-primary">当前显示 {{ workspace.filteredFieldProfiles.length }}</span>
        </div>

        <div v-if="workspace.filteredFieldProfiles.length" class="dictionary-grid">
          <article
            v-for="profile in workspace.filteredFieldProfiles"
            :key="profile.name"
            class="dictionary-item"
          >
            <div class="dictionary-item-head">
              <div>
                <h4>{{ profile.name }}</h4>
                <p>{{ profile.summary }}</p>
              </div>
              <div class="dictionary-item-tags">
                <span class="badge badge-soft">
                  {{ workspace.formatDetectedTypeLabel(profile.detected_type) }}
                </span>
                <span class="badge badge-soft">{{ profile.role_hint }}</span>
              </div>
            </div>

            <div class="dictionary-meta-grid">
              <div class="quality-card compact-quality-card">
                <span class="quality-label">原始类型</span>
                <strong class="quality-value small">{{ profile.dtype }}</strong>
              </div>
              <div class="quality-card compact-quality-card">
                <span class="quality-label">非空值</span>
                <strong class="quality-value small">{{ profile.non_null_count }}</strong>
              </div>
              <div class="quality-card compact-quality-card">
                <span class="quality-label">缺失率</span>
                <strong class="quality-value small">{{ workspace.formatPercent(profile.missing_ratio * 100) }}</strong>
              </div>
              <div class="quality-card compact-quality-card">
                <span class="quality-label">唯一值</span>
                <strong class="quality-value small">{{ profile.unique_count }}</strong>
              </div>
            </div>

            <div v-if="profile.sample_values?.length" class="dictionary-chip-section">
              <strong>样本值</strong>
              <div class="dictionary-chip-list">
                <span
                  v-for="(sample, sampleIndex) in profile.sample_values"
                  :key="`${profile.name}-sample-${sampleIndex}`"
                  class="badge badge-primary"
                >
                  {{ sample }}
                </span>
              </div>
            </div>

            <div v-if="profile.top_values?.length" class="dictionary-chip-section">
              <strong>高频值</strong>
              <div class="dictionary-chip-list">
                <span
                  v-for="(item, topIndex) in profile.top_values"
                  :key="`${profile.name}-top-${topIndex}`"
                  class="badge badge-soft"
                >
                  {{ item.value }} · {{ item.count }} 次 · {{ workspace.formatPercent(item.percentage) }}
                </span>
              </div>
            </div>

            <div class="dictionary-chip-section">
              <strong>推荐用途</strong>
              <div class="dictionary-chip-list">
                <span
                  v-for="(use, useIndex) in profile.recommended_uses"
                  :key="`${profile.name}-use-${useIndex}`"
                  class="badge badge-primary"
                >
                  {{ use }}
                </span>
              </div>
            </div>

            <div
              v-if="profile.detected_type === 'numeric' && profile.numeric_summary"
              class="groupby-note compact-note"
            >
              <strong>数值概览</strong>
              <span>
                范围 {{ profile.numeric_summary.min }} ~ {{ profile.numeric_summary.max }}，
                均值 {{ profile.numeric_summary.mean ?? "-" }}，
                中位数 {{ profile.numeric_summary.median ?? "-" }}，
                标准差 {{ profile.numeric_summary.std ?? "-" }}
              </span>
            </div>

            <div
              v-else-if="profile.detected_type === 'datetime' && profile.datetime_summary"
              class="groupby-note compact-note"
            >
              <strong>时间范围</strong>
              <span>
                {{ profile.datetime_summary.min }} ~ {{ profile.datetime_summary.max }}
              </span>
            </div>
          </article>
        </div>

        <div v-else class="empty-state compact-empty">
          <strong>没有匹配的字段</strong>
          <span>换个关键词或字段类型试试，系统会继续保留完整字段画像数据。</span>
        </div>
      </template>

      <div v-else class="empty-state">
        <strong>还没有字段画像</strong>
        <span>选择文件后，系统会自动生成字段画像和数据字典。</span>
      </div>
    </div>
  </section>
</template>

<script setup>
import { inject } from "vue";

const workspace = inject("workspaceCtx");
</script>
