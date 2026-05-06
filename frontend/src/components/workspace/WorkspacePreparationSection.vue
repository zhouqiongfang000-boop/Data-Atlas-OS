<template>
  <section v-show="workspace.activeWorkspaceSection === 'preparation'" class="workspace-section-panel">
    <div class="surface-card panel-card cleaning-card">
      <div class="panel-overline">Quality & Cleaning</div>
      <div class="panel-header">
        <div>
          <div class="panel-title-row">
            <h3 class="section-title">数据质量与清洗</h3>
            <button
              type="button"
              class="panel-help-trigger"
              :class="{ active: workspace.isPanelHelpOpen('cleaning') }"
              aria-label="查看数据质量与清洗说明"
              @click="workspace.togglePanelHelp('cleaning')"
            >
              !
            </button>
          </div>
          <p class="section-subtitle">先检查缺失值和重复值，再预览清洗结果，最后另存为新文件继续分析</p>
        </div>
        <span class="badge badge-primary" v-if="workspace.qualityReport">
          {{ workspace.qualityReport.row_count }} 行
        </span>
      </div>
      <div v-if="workspace.isPanelHelpOpen('cleaning')" class="panel-help-box">
        <strong>{{ workspace.panelHelpContent.cleaning.title }}</strong>
        <span>{{ workspace.panelHelpContent.cleaning.body }}</span>
      </div>

      <div v-if="workspace.loadingQuality" class="empty-state">
        <strong>质量检查中</strong>
        <span>正在扫描当前文件的缺失值、重复值和字段类型...</span>
      </div>

      <template v-else-if="workspace.qualityReport">
        <div class="quality-grid">
          <div class="quality-card">
            <span class="quality-label">缺失单元格</span>
            <strong class="quality-value">{{ workspace.qualityReport.missing_cell_count }}</strong>
          </div>
          <div class="quality-card">
            <span class="quality-label">含缺失字段</span>
            <strong class="quality-value">{{ workspace.qualityReport.columns_with_missing }}</strong>
          </div>
          <div class="quality-card">
            <span class="quality-label">重复行</span>
            <strong class="quality-value">{{ workspace.qualityReport.duplicate_row_count }}</strong>
          </div>
          <div class="quality-card">
            <span class="quality-label">异常候选单元格</span>
            <strong class="quality-value">{{ workspace.qualityReport.outlier_cell_count }}</strong>
          </div>
          <div class="quality-card">
            <span class="quality-label">异常候选行</span>
            <strong class="quality-value">{{ workspace.qualityReport.outlier_row_count }}</strong>
          </div>
          <div class="quality-card">
            <span class="quality-label">字段总数</span>
            <strong class="quality-value">{{ workspace.qualityReport.column_count }}</strong>
          </div>
        </div>

        <div class="quality-controls">
          <div class="inline-field">
            <span>缺失值处理</span>
            <div class="option-pill-group">
              <button
                v-for="option in workspace.CLEANING_MISSING_OPTIONS"
                :key="option.value"
                type="button"
                class="option-pill"
                :class="{ active: workspace.cleaningForm.missingStrategy === option.value }"
                @click="workspace.setMissingStrategy(option.value)"
              >
                {{ option.label }}
              </button>
            </div>
          </div>

          <div class="inline-field">
            <span>候选异常处理</span>
            <div class="option-pill-group">
              <button
                v-for="option in workspace.CLEANING_OUTLIER_OPTIONS"
                :key="option.value"
                type="button"
                class="option-pill"
                :class="{ active: workspace.cleaningForm.outlierStrategy === option.value }"
                @click="workspace.setOutlierStrategy(option.value)"
              >
                {{ option.label }}
              </button>
            </div>
          </div>

          <div class="conversion-builder">
            <span>数据类型转换</span>
            <div class="conversion-builder-row">
              <label class="inline-field conversion-select-field">
                <span>选择字段</span>
                <select v-model="workspace.cleaningForm.conversionColumn" class="theme-select">
                  <option value="">请选择字段</option>
                  <option
                    v-for="columnName in workspace.availableConversionColumns"
                    :key="columnName"
                    :value="columnName"
                  >
                    {{ columnName }}
                  </option>
                </select>
              </label>

              <div class="inline-field conversion-target-field">
                <span>目标类型</span>
                <div class="option-pill-group compact-pill-group">
                  <button
                    v-for="option in workspace.TYPE_CONVERSION_OPTIONS"
                    :key="option.value"
                    type="button"
                    class="option-pill"
                    :class="{ active: workspace.cleaningForm.conversionTargetType === option.value }"
                    @click="workspace.cleaningForm.conversionTargetType = option.value"
                  >
                    {{ option.label }}
                  </button>
                </div>
              </div>

              <button type="button" class="btn btn-ghost add-rule-btn" @click="workspace.addTypeConversion">
                添加规则
              </button>
            </div>

            <div v-if="workspace.cleaningForm.typeConversions.length" class="conversion-rule-list">
              <span
                v-for="item in workspace.cleaningForm.typeConversions"
                :key="item.column"
                class="conversion-rule-chip"
              >
                {{ item.column }} → {{ workspace.formatConversionTargetLabel(item.targetType) }}
                <button type="button" @click="workspace.removeTypeConversion(item.column)">移除</button>
              </span>
            </div>
          </div>

          <label v-if="workspace.cleaningForm.missingStrategy === 'fill_fixed'" class="inline-field">
            <span>固定填充值</span>
            <input
              v-model="workspace.cleaningForm.fillValue"
              type="text"
              placeholder="例如 0、未知、N/A"
            />
          </label>

          <label class="checkbox-field">
            <input v-model="workspace.cleaningForm.removeDuplicates" type="checkbox" />
            <span>同时删除重复行</span>
          </label>

          <div class="quality-actions">
            <button
              class="btn btn-ghost"
              :disabled="workspace.loadingCleaningPreview || workspace.applyingCleaning"
              @click="workspace.previewCleaning"
            >
              {{ workspace.loadingCleaningPreview ? "预览生成中..." : "预览清洗结果" }}
            </button>
            <button
              class="btn btn-primary"
              :disabled="workspace.applyingCleaning || workspace.loadingCleaningPreview"
              @click="workspace.applyCleaning"
            >
              {{ workspace.applyingCleaning ? "正在另存..." : "应用并另存为新文件" }}
            </button>
          </div>
        </div>

        <div class="table-shell quality-table-shell">
          <table class="data-table">
            <thead>
              <tr>
                <th>字段</th>
                <th>识别类型</th>
                <th>原始类型</th>
                <th>缺失值</th>
                <th>缺失率</th>
                <th>异常候选</th>
                <th>候选率</th>
                <th>检测说明</th>
                <th>唯一值</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="column in workspace.qualityColumns" :key="column.name">
                <tr>
                  <td>{{ column.name }}</td>
                  <td>{{ workspace.formatDetectedTypeLabel(column.detected_type) }}</td>
                  <td>{{ column.dtype }}</td>
                  <td>{{ column.missing_count }}</td>
                  <td>{{ (column.missing_ratio * 100).toFixed(1) }}%</td>
                  <td>{{ column.outlier_count }}</td>
                  <td>{{ (column.outlier_ratio * 100).toFixed(1) }}%</td>
                  <td class="detail-cell">
                    <div class="detail-summary">{{ workspace.formatOutlierDetail(column) }}</div>
                    <button
                      v-if="column.outlier_count"
                      type="button"
                      class="detail-toggle"
                      @click="workspace.toggleOutlierDetail(column)"
                    >
                      {{
                        workspace.expandedOutlierColumn === column.name
                          ? "收起候选记录"
                          : "查看候选记录"
                      }}
                    </button>
                  </td>
                  <td>{{ column.unique_count }}</td>
                </tr>

                <tr
                  v-if="workspace.expandedOutlierColumn === column.name"
                  class="detail-expand-row"
                >
                  <td colspan="9">
                    <div class="outlier-expanded-card">
                      <div
                        v-if="workspace.loadingOutlierColumn === column.name"
                        class="empty-state compact-empty"
                      >
                        <strong>候选记录加载中</strong>
                        <span>正在读取触发统计候选的完整行数据...</span>
                      </div>

                      <template v-else-if="workspace.outlierDetailMap[column.name]">
                        <div class="cleaning-preview-meta">
                          <span class="badge badge-primary">
                            候选数量：{{ workspace.outlierDetailMap[column.name].count }}
                          </span>
                          <span
                            v-if="
                              workspace.outlierDetailMap[column.name].bounds &&
                              workspace.outlierDetailMap[column.name].bounds.method_label
                            "
                            class="badge badge-primary"
                          >
                            检测方式：
                            {{ workspace.outlierDetailMap[column.name].bounds.method_label }}
                          </span>
                          <span
                            v-if="
                              workspace.outlierDetailMap[column.name].bounds &&
                              workspace.outlierDetailMap[column.name].bounds.lower_bound !== undefined &&
                              workspace.outlierDetailMap[column.name].bounds.upper_bound !== undefined
                            "
                            class="badge badge-primary"
                          >
                            检测区间：
                            {{ workspace.outlierDetailMap[column.name].bounds.lower_bound }}
                            ~
                            {{ workspace.outlierDetailMap[column.name].bounds.upper_bound }}
                          </span>
                        </div>

                        <div
                          v-if="workspace.outlierDetailMap[column.name].rows?.length"
                          class="table-shell inner-detail-shell"
                        >
                          <table class="data-table compact-detail-table">
                            <thead>
                              <tr>
                                <th
                                  v-for="detailColumn in workspace.outlierDetailMap[column.name].columns"
                                  :key="detailColumn"
                                >
                                  {{ workspace.formatOutlierColumnLabel(detailColumn) }}
                                </th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr
                                v-for="(detailRow, detailIndex) in workspace.outlierDetailMap[column.name].rows"
                                :key="detailIndex"
                              >
                                <td
                                  v-for="detailColumn in workspace.outlierDetailMap[column.name].columns"
                                  :key="detailColumn"
                                >
                                  {{ detailRow[detailColumn] }}
                                </td>
                              </tr>
                            </tbody>
                          </table>
                        </div>

                        <div v-else class="empty-state compact-empty">
                          <strong>没有候选记录样本</strong>
                          <span>当前字段没有检测到可展示的候选记录</span>
                        </div>
                      </template>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>

        <div v-if="workspace.cleaningPreview" class="cleaning-preview">
          <div class="panel-header compact-header">
            <div>
              <h4 class="section-title">清洗结果预览</h4>
              <p class="section-subtitle">先对比变化，再决定是否另存为新文件</p>
            </div>
            <span class="badge badge-success">
              {{ workspace.cleaningPreview.result_summary.row_count }} 行
            </span>
          </div>

          <div class="cleaning-preview-meta">
            <span class="badge badge-primary">
              原始行数：{{ workspace.cleaningPreview.source_summary.row_count }}
            </span>
            <span class="badge badge-primary">
              清洗后行数：{{ workspace.cleaningPreview.result_summary.row_count }}
            </span>
            <span class="badge badge-primary">
              清洗后缺失值：{{ workspace.cleaningPreview.result_summary.missing_cell_count }}
            </span>
            <span class="badge badge-primary">
              清洗后候选异常行：{{ workspace.cleaningPreview.result_summary.outlier_row_count }}
            </span>
          </div>

          <div v-if="workspace.cleaningPreview.operations?.length" class="cleaning-operation-list">
            <span
              v-for="(operation, index) in workspace.cleaningPreview.operations"
              :key="index"
              class="badge badge-soft"
            >
              {{ operation.label }}
            </span>
          </div>

          <div v-if="workspace.cleaningPreviewColumns.length" class="table-shell">
            <table class="data-table">
              <thead>
                <tr>
                  <th v-for="col in workspace.cleaningPreviewColumns" :key="col">
                    {{ col }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, rowIndex) in workspace.cleaningPreviewRows" :key="rowIndex">
                  <td v-for="col in workspace.cleaningPreviewColumns" :key="col">
                    {{ row[col] }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>

      <div v-else class="empty-state">
        <strong>还没有质量检查结果</strong>
        <span>选择文件后，系统会自动扫描缺失值、重复值和字段类型</span>
      </div>
    </div>

    <div class="surface-card panel-card cleaning-history-card">
      <div class="panel-overline">Cleaning Timeline</div>
      <div class="panel-header">
        <div>
          <div class="panel-title-row">
            <h3 class="section-title">清洗历史与回滚</h3>
            <button
              type="button"
              class="panel-help-trigger"
              :class="{ active: workspace.isPanelHelpOpen('cleaningHistory') }"
              aria-label="查看清洗历史与回滚说明"
              @click="workspace.togglePanelHelp('cleaningHistory')"
            >
              !
            </button>
          </div>
          <p class="section-subtitle">看清当前文件是如何一步步清洗出来的，并快速回到处理前版本</p>
        </div>
        <span class="badge badge-primary" v-if="workspace.cleaningHistory.lineage?.length">
          {{ workspace.cleaningHistory.lineage.length }} 步
        </span>
      </div>
      <div v-if="workspace.isPanelHelpOpen('cleaningHistory')" class="panel-help-box">
        <strong>{{ workspace.panelHelpContent.cleaningHistory.title }}</strong>
        <span>{{ workspace.panelHelpContent.cleaningHistory.body }}</span>
      </div>

      <div v-if="workspace.loadingCleaningHistory" class="empty-state">
        <strong>清洗历史加载中</strong>
        <span>正在梳理当前文件的清洗链路...</span>
      </div>

      <div v-else-if="!workspace.selectedFile" class="empty-state">
        <strong>先选择文件</strong>
        <span>选定数据文件后，系统会展示这份文件的清洗链路和可回滚节点。</span>
      </div>

      <template v-else>
        <div v-if="workspace.cleaningHistory.current_file" class="groupby-note subtle">
          <strong>当前文件：{{ workspace.cleaningHistory.current_file.name }}</strong>
          <span>如果这是清洗版本，可以沿着下面的历史节点回到处理前文件，或生成一个新的回滚文件。</span>
        </div>

        <div v-if="workspace.cleaningHistory.lineage?.length" class="cleaning-history-list">
          <div
            v-for="item in workspace.cleaningHistory.lineage"
            :key="item.id"
            class="cleaning-history-item"
          >
            <div class="cleaning-history-head">
              <div>
                <strong>{{ item.source_file_name }} → {{ item.result_file_name }}</strong>
                <span>{{ workspace.formatDateTime(item.created_at) }}</span>
              </div>
            </div>

            <div class="cleaning-history-meta">
              <span
                v-for="(label, labelIndex) in item.operation_labels"
                :key="`${item.id}-${labelIndex}`"
                class="badge badge-soft"
              >
                {{ label }}
              </span>
            </div>

            <div class="groupby-note">
              <strong>这一步做了什么</strong>
              <span>{{ workspace.formatCleaningOperationLabels(item) }}</span>
            </div>

            <div class="cleaning-history-actions">
              <button
                type="button"
                class="btn btn-ghost"
                @click="workspace.jumpToCleaningHistoryFile(item.source_stored_name)"
              >
                查看处理前文件
              </button>
              <button
                type="button"
                class="btn btn-primary"
                :disabled="workspace.rollingBackHistoryId === item.id"
                @click="workspace.rollbackCleaningHistory(item)"
              >
                {{ workspace.rollingBackHistoryId === item.id ? "回滚生成中..." : "回滚并另存为新文件" }}
              </button>
            </div>
          </div>
        </div>

        <div v-else class="empty-state compact-empty">
          <strong>当前文件还没有上游清洗链路</strong>
          <span>这通常说明它是原始文件，或者还没有经过清洗另存。</span>
        </div>

        <div v-if="workspace.cleaningHistory.descendants?.length" class="cleaning-descendant-panel">
          <div class="panel-header compact-header">
            <div>
              <h4 class="section-title">从当前文件生成的版本</h4>
              <p class="section-subtitle">这些是基于当前文件继续清洗或回滚后另存出来的新版本</p>
            </div>
          </div>
          <div class="cleaning-history-list compact">
            <div
              v-for="item in workspace.cleaningHistory.descendants"
              :key="`child-${item.id}`"
              class="cleaning-history-item"
            >
              <div class="cleaning-history-head">
                <div>
                  <strong>{{ item.result_file_name }}</strong>
                  <span>{{ workspace.formatDateTime(item.created_at) }}</span>
                </div>
              </div>
              <div class="cleaning-history-meta">
                <span
                  v-for="(label, labelIndex) in item.operation_labels"
                  :key="`child-${item.id}-${labelIndex}`"
                  class="badge badge-soft"
                >
                  {{ label }}
                </span>
              </div>
              <div class="cleaning-history-actions">
                <button
                  type="button"
                  class="btn btn-ghost"
                  @click="workspace.jumpToCleaningHistoryFile(item.result_stored_name)"
                >
                  切换到这个版本
                </button>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </section>
</template>

<script setup>
import { inject } from "vue";

const workspace = inject("workspaceCtx");
</script>
