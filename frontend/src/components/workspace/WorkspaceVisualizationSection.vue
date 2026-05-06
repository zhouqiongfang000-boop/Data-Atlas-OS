<template>
  <section v-show="workspace.activeWorkspaceSection === 'visualization'" class="workspace-section-panel">
    <div class="surface-card panel-card chart-card">
      <div class="panel-overline">Visualization Deck</div>
      <div class="panel-header">
        <div>
          <div class="panel-title-row">
            <h3 class="section-title">图表分析</h3>
            <button
              type="button"
              class="panel-help-trigger"
              :class="{ active: workspace.isPanelHelpOpen('chart') }"
              aria-label="查看图表分析说明"
              @click="workspace.togglePanelHelp('chart')"
            >
              !
            </button>
          </div>
          <p class="section-subtitle">用统一的图表工作台切换字段、图形类型和展示角度</p>
        </div>
      </div>
      <div v-if="workspace.isPanelHelpOpen('chart')" class="panel-help-box">
        <strong>{{ workspace.panelHelpContent.chart.title }}</strong>
        <span>{{ workspace.panelHelpContent.chart.body }}</span>
      </div>

      <div v-if="workspace.currentColumn" class="chart-guidance">{{ workspace.chartPanelSubtitle }}</div>

      <div v-if="workspace.analysis?.numeric_columns?.length" class="column-toolbar">
        <button
          v-for="col in workspace.analysis.numeric_columns"
          :key="col"
          class="field-chip"
          :class="{ active: workspace.currentColumn === col }"
          @click="workspace.selectChartColumn(col)"
        >
          {{ col }}
        </button>
      </div>

      <div v-if="workspace.analysis?.categorical_columns?.length" class="column-toolbar">
        <button
          v-for="col in workspace.analysis.categorical_columns"
          :key="col"
          class="field-chip"
          :class="{ active: workspace.currentColumn === col }"
          @click="workspace.selectChartColumn(col)"
        >
          {{ col }}
        </button>
      </div>

      <div v-if="workspace.currentColumn" class="chart-type-toolbar">
        <button
          v-for="option in workspace.currentChartOptions"
          :key="option.value"
          class="field-chip"
          :class="{ active: workspace.currentChartType === option.value }"
          @click="workspace.loadChart(workspace.currentColumn, option.value)"
        >
          {{ option.label }}
        </button>
      </div>

      <div v-if="workspace.loadingChart" class="empty-state">
        <strong>图表生成中</strong>
        <span>正在根据当前字段构建可视化结果...</span>
      </div>

      <div v-else-if="workspace.chartData" class="chart-panel">
        <div class="chart-meta">
          <span class="badge badge-success">{{ workspace.currentColumnKindLabel }}</span>
          <span class="badge badge-primary">{{ workspace.currentChartTypeLabel }}</span>
          <span class="badge badge-primary">当前字段：{{ workspace.currentColumn }}</span>
        </div>
        <div class="chart-info-grid">
          <div class="quality-card chart-info-card">
            <span class="quality-label">图表标题</span>
            <strong class="chart-info-value">{{ workspace.activeChartPresentation.title }}</strong>
          </div>
          <div class="quality-card chart-info-card">
            <span class="quality-label">
              {{ workspace.activeChartPresentation.primaryLabelName }}
            </span>
            <strong class="chart-info-value">{{ workspace.activeChartPresentation.xAxisLabel }}</strong>
          </div>
          <div class="quality-card chart-info-card">
            <span class="quality-label">
              {{ workspace.activeChartPresentation.secondaryLabelName }}
            </span>
            <strong class="chart-info-value">{{ workspace.activeChartPresentation.yAxisLabel }}</strong>
          </div>
        </div>
        <div class="chart-export-toolbar">
          <div class="chart-export-note">
            <strong>导出说明</strong>
            <span v-if="workspace.showChartExportPanel">
              现在可以在下方修改导出标题和坐标轴文案，图表预览会同步更新。
            </span>
            <span v-else>
              标题和坐标轴文案会根据当前图表自动生成；点击“准备导出图表”后，可临时修改后再导出。
            </span>
          </div>
          <div class="chart-export-actions">
            <button
              v-if="!workspace.showChartExportPanel"
              type="button"
              class="btn btn-ghost"
              @click="workspace.openChartExportPanel"
            >
              准备导出图表
            </button>
            <template v-else>
              <button type="button" class="btn btn-ghost" @click="workspace.cancelChartExportPanel">
                取消
              </button>
              <button
                type="button"
                class="btn btn-primary"
                :disabled="workspace.exportingTarget === 'chart'"
                @click="workspace.exportChartImage"
              >
                {{ workspace.exportingTarget === "chart" ? "导出中..." : "导出 PNG" }}
              </button>
            </template>
          </div>
        </div>
        <div v-if="workspace.showChartExportPanel" class="chart-export-panel">
          <div class="chart-export-grid">
            <label class="inline-field">
              <span>导出标题</span>
              <input
                v-model="workspace.chartExportForm.title"
                type="text"
                placeholder="可在导出前修改标题"
              />
            </label>

            <template v-if="workspace.activeChartPresentation.usesCartesianAxes">
              <label class="inline-field">
                <span>{{ workspace.activeChartPresentation.primaryLabelName }}</span>
                <input
                  v-model="workspace.chartExportForm.xAxisLabel"
                  type="text"
                  placeholder="请输入横轴文案"
                />
              </label>

              <label class="inline-field">
                <span>{{ workspace.activeChartPresentation.secondaryLabelName }}</span>
                <input
                  v-model="workspace.chartExportForm.yAxisLabel"
                  type="text"
                  placeholder="请输入纵轴文案"
                />
              </label>
            </template>
          </div>

          <div class="groupby-note subtle">
            <strong>预览提示</strong>
            <span v-if="workspace.activeChartPresentation.usesCartesianAxes">
              这里修改的标题和坐标轴文案只用于本次导出，导出完成后会恢复为默认自动生成的内容。
            </span>
            <span v-else>
              当前图表不使用传统横纵坐标轴，你可以先调整导出标题，再进行导出。
            </span>
          </div>
        </div>
        <div :ref="(el) => (workspace.chartRef = el)" class="chart-box"></div>
      </div>

      <div v-else class="empty-state">
        <strong>还没有图表结果</strong>
        <span>先选择一个字段，系统会根据字段类型加载可用图形</span>
      </div>
    </div>

    <div class="surface-card panel-card prediction-card">
      <div class="panel-overline">Machine Learning Forecast</div>
      <div class="panel-header compact-header">
        <div>
          <div class="panel-title-row">
            <h3 class="section-title">数据预测</h3>
            <button
              type="button"
              class="panel-help-trigger"
              :class="{ active: workspace.isPanelHelpOpen('predict') }"
              aria-label="查看数据预测说明"
              @click="workspace.togglePanelHelp('predict')"
            >
              !
            </button>
          </div>
          <p class="section-subtitle">使用数据挖掘与机器学习模型预测未来数据，并生成预测趋势图</p>
        </div>
      </div>
      <div v-if="workspace.isPanelHelpOpen('predict')" class="panel-help-box">
        <strong>{{ workspace.panelHelpContent.predict.title }}</strong>
        <span>{{ workspace.panelHelpContent.predict.body }}</span>
      </div>

      <div v-if="workspace.availablePredictionTargetColumns.length" class="prediction-builder">
        <label class="inline-field">
          <span>预测目标</span>
          <select v-model="workspace.predictionForm.targetColumn">
            <option
              v-for="column in workspace.availablePredictionTargetColumns"
              :key="column"
              :value="column"
            >
              {{ column }}
            </option>
          </select>
        </label>

        <label class="inline-field">
          <span>趋势依据</span>
          <select v-model="workspace.predictionForm.featureColumn">
            <option value="">行号序列</option>
            <option
              v-for="column in workspace.availablePredictionFeatureColumns"
              :key="column"
              :value="column"
            >
              {{ column }}
            </option>
          </select>
        </label>

        <label class="inline-field">
          <span>预测步数</span>
          <input
            v-model.number="workspace.predictionForm.periods"
            type="number"
            min="1"
            max="60"
            step="1"
          />
        </label>

        <div class="prediction-actions">
          <button
            type="button"
            class="btn btn-primary"
            :disabled="workspace.loadingPrediction"
            @click="workspace.runPrediction"
          >
            {{ workspace.loadingPrediction ? "预测中..." : "生成预测" }}
          </button>
        </div>
      </div>

      <div v-if="workspace.loadingPrediction" class="empty-state">
        <strong>模型计算中</strong>
        <span>正在清洗有效样本、拟合趋势并生成未来预测...</span>
      </div>

      <div v-else-if="workspace.predictionResult" class="prediction-result">
        <div class="chart-meta">
          <span class="badge badge-success">{{ workspace.predictionResult.model_name }}</span>
          <span class="badge badge-primary">目标：{{ workspace.predictionResult.target_column }}</span>
          <span class="badge badge-primary">趋势：{{ workspace.predictionResult.trend }}</span>
          <span class="badge badge-primary">{{ workspace.predictionResult.confidence_label }}</span>
        </div>

        <div class="prediction-summary-grid">
          <div class="quality-card chart-info-card">
            <span class="quality-label">样本量</span>
            <strong class="chart-info-value">{{ workspace.predictionResult.metrics.sample_count }}</strong>
          </div>
          <div class="quality-card chart-info-card">
            <span class="quality-label">R²</span>
            <strong class="chart-info-value">{{ workspace.predictionResult.metrics.r2 ?? "-" }}</strong>
          </div>
          <div class="quality-card chart-info-card">
            <span class="quality-label">MAE</span>
            <strong class="chart-info-value">{{ workspace.predictionResult.metrics.mae }}</strong>
          </div>
          <div class="quality-card chart-info-card">
            <span class="quality-label">RMSE</span>
            <strong class="chart-info-value">{{ workspace.predictionResult.metrics.rmse }}</strong>
          </div>
        </div>

        <div class="chart-panel prediction-chart-panel">
          <div
            :ref="(el) => (workspace.predictionChartRef = el)"
            class="chart-box prediction-chart-box"
          ></div>
        </div>

        <div class="table-shell prediction-table-shell">
          <table class="data-table">
            <thead>
              <tr>
                <th>未来节点</th>
                <th>预测值</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in workspace.predictionResult.forecast" :key="item.label">
                <td>{{ item.label }}</td>
                <td>{{ item.value }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-else class="empty-state">
        <strong>暂无预测结果</strong>
        <span>选择数值字段后，可预测未来趋势并生成图表</span>
      </div>
    </div>

    <section class="insight-grid">
      <div class="surface-card panel-card">
        <div class="panel-overline">Descriptive Statistics</div>
        <div class="panel-header compact-header">
          <div>
            <div class="panel-title-row">
              <h3 class="section-title">描述性统计</h3>
              <button
                type="button"
                class="panel-help-trigger"
                :class="{ active: workspace.isPanelHelpOpen('stats') }"
                aria-label="查看描述性统计说明"
                @click="workspace.togglePanelHelp('stats')"
              >
                !
              </button>
            </div>
            <p class="section-subtitle">展示 count、mean、std、min、max 等关键指标</p>
          </div>
        </div>
        <div v-if="workspace.isPanelHelpOpen('stats')" class="panel-help-box">
          <strong>{{ workspace.panelHelpContent.stats.title }}</strong>
          <span>{{ workspace.panelHelpContent.stats.body }}</span>
        </div>

        <div v-if="workspace.statRows.length" class="result-export-toolbar">
          <button
            type="button"
            class="btn btn-ghost"
            :disabled="workspace.exportingTarget === 'statistics'"
            @click="workspace.exportStatisticsResult"
          >
            {{ workspace.exportingTarget === "statistics" ? "导出中..." : "导出描述统计" }}
          </button>
        </div>

        <div v-if="workspace.loadingAnalysis" class="empty-state">
          <strong>统计分析中</strong>
          <span>正在生成描述性统计结果...</span>
        </div>

        <div v-else-if="workspace.statRows.length" class="table-shell">
          <table class="data-table">
            <thead>
              <tr>
                <th>字段</th>
                <th>count</th>
                <th>mean</th>
                <th>std</th>
                <th>min</th>
                <th>25%</th>
                <th>50%</th>
                <th>75%</th>
                <th>max</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in workspace.statRows" :key="item.name">
                <td>{{ item.name }}</td>
                <td>{{ item.count }}</td>
                <td>{{ item.mean }}</td>
                <td>{{ item.std }}</td>
                <td>{{ item.min }}</td>
                <td>{{ item.q1 }}</td>
                <td>{{ item.median }}</td>
                <td>{{ item.q3 }}</td>
                <td>{{ item.max }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-else class="empty-state">
          <strong>暂无统计结果</strong>
          <span>选择文件后，系统会自动生成描述统计</span>
        </div>
      </div>

      <div class="surface-card panel-card">
        <div class="panel-overline">Correlation Matrix</div>
        <div class="panel-header compact-header">
          <div>
            <div class="panel-title-row">
              <h3 class="section-title">相关性分析</h3>
              <button
                type="button"
                class="panel-help-trigger"
                :class="{ active: workspace.isPanelHelpOpen('correlation') }"
                aria-label="查看相关性分析说明"
                @click="workspace.togglePanelHelp('correlation')"
              >
                !
              </button>
            </div>
            <p class="section-subtitle">展示数值字段之间的相关系数矩阵</p>
          </div>
        </div>
        <div v-if="workspace.isPanelHelpOpen('correlation')" class="panel-help-box">
          <strong>{{ workspace.panelHelpContent.correlation.title }}</strong>
          <span>{{ workspace.panelHelpContent.correlation.body }}</span>
        </div>

        <div v-if="workspace.correlationRows.length" class="correlation-view-toolbar">
          <button
            v-for="option in workspace.CORRELATION_VIEW_OPTIONS"
            :key="option.value"
            type="button"
            class="field-chip"
            :class="{ active: workspace.correlationView === option.value }"
            @click="workspace.setCorrelationView(option.value)"
          >
            {{ option.label }}
          </button>
          <button
            type="button"
            class="btn btn-ghost"
            :disabled="workspace.exportingTarget === 'correlation'"
            @click="workspace.exportCorrelationResult"
          >
            {{ workspace.exportingTarget === "correlation" ? "导出中..." : "导出相关矩阵" }}
          </button>
        </div>

        <div
          v-if="workspace.correlationRows.length && workspace.correlationView === 'heatmap'"
          class="correlation-filter-toolbar"
        >
          <span class="correlation-filter-label">相关阈值</span>
          <button
            v-for="option in workspace.CORRELATION_THRESHOLD_OPTIONS"
            :key="option.label"
            type="button"
            class="field-chip"
            :class="{ active: workspace.correlationAbsThreshold === option.value }"
            @click="workspace.setCorrelationAbsThreshold(option.value)"
          >
            {{ option.label }}
          </button>
        </div>

        <div
          v-if="workspace.correlationRows.length && workspace.correlationView === 'heatmap'"
          class="chart-panel correlation-chart-panel"
        >
          <div class="chart-meta">
            <span class="badge badge-success">
              数值字段 {{ workspace.analysis.numeric_columns.length }} 个
            </span>
            <span class="badge badge-primary">相关矩阵热力图</span>
            <span class="badge badge-primary">
              可见相关对 {{ workspace.visibleCorrelationPairCount }} 组
            </span>
          </div>
          <div
            :ref="(el) => (workspace.correlationChartRef = el)"
            class="chart-box correlation-chart-box"
            :style="{ height: workspace.correlationChartHeight }"
          ></div>
        </div>

        <div v-else-if="workspace.correlationRows.length" class="table-shell">
          <table class="data-table">
            <thead>
              <tr>
                <th>字段</th>
                <th v-for="col in workspace.analysis.numeric_columns" :key="col">{{ col }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in workspace.correlationRows" :key="row.name">
                <td>{{ row.name }}</td>
                <td v-for="col in workspace.analysis.numeric_columns" :key="col">
                  {{ row[col] }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-else class="empty-state">
          <strong>暂无相关性矩阵</strong>
          <span>请选择包含数值字段的数据文件后再查看</span>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup>
import { inject } from "vue";

const workspace = inject("workspaceCtx");
</script>
