<template>
  <section v-show="workspace.activeWorkspaceSection === 'exploration'" class="workspace-section-panel">
    <div class="surface-card panel-card query-card">
      <div class="panel-overline">Query Studio</div>
      <div class="panel-header">
        <div>
          <div class="panel-title-row">
            <h3 class="section-title">查询与筛选</h3>
            <button
              type="button"
              class="panel-help-trigger"
              :class="{ active: workspace.isPanelHelpOpen('query') }"
              aria-label="查看查询与筛选说明"
              @click="workspace.togglePanelHelp('query')"
            >
              !
            </button>
          </div>
          <p class="section-subtitle">对当前文件做条件筛选、排序和分页预览，为后续分组统计和热力图打底</p>
        </div>
        <span class="badge badge-primary" v-if="workspace.queryPreviewResult">
          {{ workspace.queryPreviewResult.filtered_rows }} / {{ workspace.queryPreviewResult.total_rows }} 行
        </span>
      </div>
      <div v-if="workspace.isPanelHelpOpen('query')" class="panel-help-box">
        <strong>{{ workspace.panelHelpContent.query.title }}</strong>
        <span>{{ workspace.panelHelpContent.query.body }}</span>
      </div>

      <div class="query-controls">
        <div class="query-builder">
          <label class="inline-field">
            <span>筛选字段</span>
            <select v-model="workspace.queryForm.filterColumn" class="theme-select">
              <option value="">请选择字段</option>
              <option
                v-for="columnName in workspace.availableQueryColumns"
                :key="columnName"
                :value="columnName"
              >
                {{ columnName }}
              </option>
            </select>
          </label>

          <label class="inline-field">
            <span>条件运算</span>
            <select v-model="workspace.queryForm.filterOperator" class="theme-select">
              <option
                v-for="option in workspace.QUERY_OPERATOR_OPTIONS"
                :key="option.value"
                :value="option.value"
              >
                {{ option.label }}
              </option>
            </select>
          </label>

          <label v-if="workspace.queryOperatorNeedsValue(workspace.queryForm.filterOperator)" class="inline-field">
            <span>条件值</span>
            <input
              v-model="workspace.queryForm.filterValue"
              type="text"
              :placeholder="
                workspace.queryForm.filterOperator === 'in'
                  ? '多个值用逗号分隔'
                  : '输入条件值'
              "
            />
          </label>

          <label v-if="workspace.queryOperatorNeedsSecondValue(workspace.queryForm.filterOperator)" class="inline-field">
            <span>第二个值</span>
            <input
              v-model="workspace.queryForm.filterSecondValue"
              type="text"
              placeholder="输入区间上界"
            />
          </label>

          <button type="button" class="btn btn-ghost add-rule-btn" @click="workspace.addQueryFilter">
            添加条件
          </button>
        </div>

        <div v-if="workspace.queryForm.filters.length" class="query-chip-list">
          <span
            v-for="(filter, index) in workspace.queryForm.filters"
            :key="`${filter.column}-${filter.operator}-${index}`"
            class="query-chip"
          >
            {{ workspace.formatQueryFilterLabel(filter) }}
            <button type="button" @click="workspace.removeQueryFilter(index)">移除</button>
          </span>
        </div>

        <div class="query-toolbar">
          <label class="inline-field">
            <span>排序字段</span>
            <select v-model="workspace.queryForm.sortColumn" class="theme-select">
              <option value="">不排序</option>
              <option
                v-for="columnName in workspace.availableQueryColumns"
                :key="columnName"
                :value="columnName"
              >
                {{ columnName }}
              </option>
            </select>
          </label>

          <label class="inline-field">
            <span>排序方向</span>
            <select v-model="workspace.queryForm.sortDirection" class="theme-select">
              <option
                v-for="option in workspace.QUERY_SORT_DIRECTION_OPTIONS"
                :key="option.value"
                :value="option.value"
              >
                {{ option.label }}
              </option>
            </select>
          </label>

          <label class="inline-field">
            <span>每页行数</span>
            <select v-model="workspace.queryForm.limit" class="theme-select">
              <option :value="10">10</option>
              <option :value="20">20</option>
              <option :value="50">50</option>
              <option :value="100">100</option>
            </select>
          </label>

          <div class="query-actions">
            <button
              class="btn btn-ghost"
              :disabled="workspace.loadingQueryPreview"
              @click="workspace.runQueryPreview(0)"
            >
              {{ workspace.loadingQueryPreview ? "查询中..." : "执行查询" }}
            </button>
            <button
              class="btn btn-ghost"
              :disabled="workspace.exportingTarget === 'query'"
              @click="workspace.exportQueryResult"
            >
              {{ workspace.exportingTarget === "query" ? "导出中..." : "导出查询结果" }}
            </button>
            <button
              class="btn btn-ghost"
              :disabled="workspace.loadingQueryPreview"
              @click="workspace.clearQueryPreview"
            >
              清空条件
            </button>
          </div>
        </div>
      </div>

      <div v-if="workspace.loadingQueryPreview" class="empty-state">
        <strong>查询结果加载中</strong>
        <span>正在根据当前条件筛选和排序数据...</span>
      </div>

      <template v-else-if="workspace.queryPreviewResult">
        <div class="query-meta-grid">
          <div class="quality-card">
            <span class="quality-label">原始总行数</span>
            <strong class="quality-value">{{ workspace.queryPreviewResult.total_rows }}</strong>
          </div>
          <div class="quality-card">
            <span class="quality-label">筛选后行数</span>
            <strong class="quality-value">{{ workspace.queryPreviewResult.filtered_rows }}</strong>
          </div>
          <div class="quality-card">
            <span class="quality-label">当前偏移量</span>
            <strong class="quality-value">{{ workspace.queryPreviewResult.offset }}</strong>
          </div>
        </div>

        <div v-if="workspace.queryPreviewColumns.length" class="table-shell query-table-shell">
          <table class="data-table">
            <thead>
              <tr>
                <th v-for="col in workspace.queryPreviewColumns" :key="col">{{ col }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in workspace.queryPreviewRows" :key="index">
                <td v-for="col in workspace.queryPreviewColumns" :key="col">
                  {{ row[col] }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="query-pagination">
          <button
            class="btn btn-ghost"
            :disabled="!workspace.queryPreviewResult.has_prev || workspace.loadingQueryPreview"
            @click="workspace.changeQueryPage('prev')"
          >
            上一页
          </button>
          <span>
            当前显示
            {{
              workspace.queryPreviewResult.filtered_rows
                ? workspace.queryPreviewResult.offset + 1
                : 0
            }}
            -
            {{
              Math.min(
                workspace.queryPreviewResult.offset + workspace.queryPreviewRows.length,
                workspace.queryPreviewResult.filtered_rows
              )
            }}
          </span>
          <button
            class="btn btn-ghost"
            :disabled="!workspace.queryPreviewResult.has_next || workspace.loadingQueryPreview"
            @click="workspace.changeQueryPage('next')"
          >
            下一页
          </button>
        </div>
      </template>

      <div v-else class="empty-state">
        <strong>还没有查询结果</strong>
        <span>设置条件后执行查询，或者直接执行默认预览查看分页结果</span>
      </div>
    </div>

    <div class="surface-card panel-card groupby-card">
      <div class="panel-overline">Group Statistics</div>
      <div class="panel-header">
        <div>
          <div class="panel-title-row">
            <h3 class="section-title">分组统计</h3>
            <button
              type="button"
              class="panel-help-trigger"
              :class="{ active: workspace.isPanelHelpOpen('groupby') }"
              aria-label="查看分组统计说明"
              @click="workspace.togglePanelHelp('groupby')"
            >
              !
            </button>
          </div>
          <p class="section-subtitle">复用当前查询条件，按一个或两个字段分组后计算计数、均值、极值等核心指标</p>
        </div>
        <span class="badge badge-primary" v-if="workspace.groupByResult">
          {{ workspace.groupByResult.group_count }} 组
        </span>
      </div>
      <div v-if="workspace.isPanelHelpOpen('groupby')" class="panel-help-box">
        <strong>{{ workspace.panelHelpContent.groupby.title }}</strong>
        <span>{{ workspace.panelHelpContent.groupby.body }}</span>
      </div>

      <div class="groupby-controls">
        <div class="groupby-builder">
          <label class="inline-field">
            <span>主分组字段</span>
            <select v-model="workspace.groupByForm.primaryGroupColumn" class="theme-select">
              <option value="">请选择字段</option>
              <option
                v-for="columnName in workspace.availableGroupColumns"
                :key="columnName"
                :value="columnName"
              >
                {{ columnName }}
              </option>
            </select>
          </label>

          <label class="inline-field">
            <span>次分组字段</span>
            <select v-model="workspace.groupByForm.secondaryGroupColumn" class="theme-select">
              <option value="">可选</option>
              <option
                v-for="columnName in workspace.availableGroupColumns"
                :key="columnName"
                :value="columnName"
              >
                {{ columnName }}
              </option>
            </select>
          </label>

          <label class="inline-field">
            <span>统计字段</span>
            <select v-model="workspace.groupByForm.metricColumn" class="theme-select">
              <option value="">请选择字段</option>
              <option
                v-for="columnName in workspace.availableGroupMetricColumns"
                :key="columnName"
                :value="columnName"
              >
                {{ columnName }}
              </option>
            </select>
          </label>

          <label class="inline-field">
            <span>结果上限</span>
            <select v-model="workspace.groupByForm.limit" class="theme-select">
              <option :value="10">10</option>
              <option :value="20">20</option>
              <option :value="50">50</option>
              <option :value="100">100</option>
            </select>
          </label>
        </div>

        <div class="groupby-aggregation-panel">
          <div class="inline-field">
            <span>聚合方式</span>
            <div class="option-pill-group">
              <button
                v-for="option in workspace.GROUP_AGGREGATION_OPTIONS"
                :key="option.value"
                type="button"
                class="option-pill"
                :disabled="!workspace.groupByForm.metricColumn && option.value !== 'count'"
                :class="{ active: workspace.groupByForm.metricAggregation === option.value }"
                @click="workspace.setGroupAggregation(option.value)"
              >
                {{ option.label }}
              </button>
            </div>
          </div>

          <div class="groupby-actions">
            <button type="button" class="btn btn-ghost add-rule-btn" @click="workspace.addGroupMetric">
              添加统计字段
            </button>
            <button
              type="button"
              class="btn btn-ghost"
              :disabled="workspace.exportingTarget === 'groupby'"
              @click="workspace.exportGroupByResult"
            >
              {{ workspace.exportingTarget === "groupby" ? "导出中..." : "导出分组结果" }}
            </button>
            <button
              type="button"
              class="btn btn-primary"
              :disabled="workspace.loadingGroupBy"
              @click="workspace.runGroupBy"
            >
              {{ workspace.loadingGroupBy ? "分析中..." : "执行分组统计" }}
            </button>
          </div>
        </div>

        <div class="groupby-note">
          <span>先选统计字段，再点一种聚合方式；结果表头会自动翻译成更易懂的中文。</span>
          <strong>分析说明</strong>
          <span>分组统计会自动复用 Query Studio 里的筛选条件；如果没有额外添加统计字段，也会默认返回每组的行数。</span>
        </div>

        <div v-if="workspace.groupByForm.metrics.length" class="conversion-rule-list">
          <span
            v-for="item in workspace.groupByForm.metrics"
            :key="item.column"
            class="conversion-rule-chip"
          >
            {{ item.column }} ·
            {{ item.aggregations.map(workspace.formatGroupAggregationLabel).join(" / ") }}
            <button type="button" @click="workspace.removeGroupMetric(item.column)">移除</button>
          </span>
        </div>
      </div>

      <div v-if="workspace.loadingGroupBy" class="empty-state">
        <strong>正在生成分组统计</strong>
        <span>正在按当前筛选条件汇总结果，请稍候...</span>
      </div>

      <template v-else-if="workspace.groupByResult">
        <div class="query-meta-grid">
          <div class="quality-card">
            <span class="quality-label">筛选后行数</span>
            <strong class="quality-value">{{ workspace.groupByResult.filtered_rows }}</strong>
          </div>
          <div class="quality-card">
            <span class="quality-label">总分组数</span>
            <strong class="quality-value">{{ workspace.groupByResult.group_count }}</strong>
          </div>
          <div class="quality-card">
            <span class="quality-label">当前显示</span>
            <strong class="quality-value">
              {{ workspace.groupByResult.displayed_group_count || workspace.groupByRows.length }}
            </strong>
          </div>
          <div class="quality-card">
            <span class="quality-label">分组路径</span>
            <strong class="groupby-value-text">{{ workspace.groupByResult.group_columns.join(" / ") }}</strong>
          </div>
        </div>

        <div v-if="workspace.groupByResult.has_more" class="groupby-note subtle">
          <strong>结果已截断</strong>
          <span>当前仅显示前 {{ workspace.groupByResult.limit }} 组，可以调大结果上限查看更多。</span>
        </div>

        <div v-if="workspace.groupByColumns.length" class="table-shell groupby-table-shell">
          <table class="data-table">
            <thead>
              <tr>
                <th v-for="col in workspace.groupByColumns" :key="col">
                  {{ workspace.formatGroupByColumnLabel(col) }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in workspace.groupByRows" :key="index">
                <td v-for="col in workspace.groupByColumns" :key="col">{{ row[col] }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <div v-else class="empty-state">
        <strong>还没有分组结果</strong>
        <span>先选择分组字段，再决定是否添加统计字段，最后执行分组统计。</span>
      </div>
    </div>

    <div class="surface-card panel-card distribution-card">
      <div class="panel-overline">Distribution Analysis</div>
      <div class="panel-header">
        <div>
          <div class="panel-title-row">
            <h3 class="section-title">频数分布分析</h3>
            <button
              type="button"
              class="panel-help-trigger"
              :class="{ active: workspace.isPanelHelpOpen('distribution') }"
              aria-label="查看频数分布分析说明"
              @click="workspace.togglePanelHelp('distribution')"
            >
              !
            </button>
          </div>
          <p class="section-subtitle">查看某个字段的值或区间出现了多少次，占了多少比例，适合看类别占比和数值集中区间</p>
        </div>
        <span class="badge badge-primary" v-if="workspace.distributionResult">
          {{ workspace.distributionResult.bucket_count }} 组
        </span>
      </div>
      <div v-if="workspace.isPanelHelpOpen('distribution')" class="panel-help-box">
        <strong>{{ workspace.panelHelpContent.distribution.title }}</strong>
        <span>{{ workspace.panelHelpContent.distribution.body }}</span>
      </div>

      <div class="distribution-controls">
        <div class="distribution-builder">
          <label class="inline-field">
            <span>分析字段</span>
            <select v-model="workspace.distributionForm.column" class="theme-select">
              <option value="">请选择字段</option>
              <option
                v-for="columnName in workspace.availableDistributionColumns"
                :key="columnName"
                :value="columnName"
              >
                {{ columnName }}
              </option>
            </select>
          </label>

          <label class="inline-field">
            <span>分析模式</span>
            <select v-model="workspace.distributionForm.mode" class="theme-select">
              <option
                v-for="option in workspace.DISTRIBUTION_MODE_OPTIONS"
                :key="option.value"
                :value="option.value"
              >
                {{ option.label }}
              </option>
            </select>
          </label>

          <label v-if="workspace.shouldShowDistributionBins" class="inline-field">
            <span>分箱数量</span>
            <select v-model="workspace.distributionForm.bins" class="theme-select">
              <option :value="5">5</option>
              <option :value="8">8</option>
              <option :value="10">10</option>
              <option :value="12">12</option>
              <option :value="15">15</option>
            </select>
          </label>

          <label class="inline-field">
            <span>排序方式</span>
            <select v-model="workspace.distributionForm.sortMode" class="theme-select">
              <option
                v-for="option in workspace.DISTRIBUTION_SORT_OPTIONS"
                :key="option.value"
                :value="option.value"
              >
                {{ option.label }}
              </option>
            </select>
          </label>

          <label class="inline-field">
            <span>结果上限</span>
            <select v-model="workspace.distributionForm.limit" class="theme-select">
              <option :value="10">10</option>
              <option :value="20">20</option>
              <option :value="30">30</option>
              <option :value="50">50</option>
            </select>
          </label>
        </div>

        <div class="distribution-toolbar">
          <label class="distribution-toggle">
            <input v-model="workspace.distributionForm.includeCumulative" type="checkbox" />
            <span>显示累计频率线</span>
          </label>

          <div class="distribution-actions">
            <button
              type="button"
              class="btn btn-ghost"
              :disabled="workspace.exportingTarget === 'distribution'"
              @click="workspace.exportDistributionResult"
            >
              {{ workspace.exportingTarget === "distribution" ? "导出中..." : "导出分布结果" }}
            </button>
            <button
              type="button"
              class="btn btn-primary"
              :disabled="workspace.loadingDistribution"
              @click="workspace.runDistributionAnalysis"
            >
              {{ workspace.loadingDistribution ? "分析中..." : "执行频数分布分析" }}
            </button>
          </div>
        </div>

        <div class="groupby-note">
          <strong>分析说明</strong>
          <span>频数分布会自动复用 Query Studio 当前的筛选条件。类别字段看占比，数值字段会先分箱再统计每个区间的频数。</span>
        </div>
      </div>

      <div v-if="workspace.loadingDistribution" class="empty-state">
        <strong>正在生成频数分布</strong>
        <span>正在根据当前筛选条件统计字段分布，请稍候...</span>
      </div>

      <template v-else-if="workspace.distributionResult">
        <div class="query-meta-grid">
          <div class="quality-card">
            <span class="quality-label">筛选后行数</span>
            <strong class="quality-value">{{ workspace.distributionResult.filtered_rows }}</strong>
          </div>
          <div class="quality-card">
            <span class="quality-label">参与分析值</span>
            <strong class="quality-value">{{ workspace.distributionResult.analyzed_rows }}</strong>
          </div>
          <div class="quality-card">
            <span class="quality-label">缺失值数量</span>
            <strong class="quality-value">{{ workspace.distributionResult.missing_rows }}</strong>
          </div>
          <div class="quality-card">
            <span class="quality-label">分析模式</span>
            <strong class="groupby-value-text">
              {{ workspace.distributionResult.resolved_mode === "numeric" ? "数值分箱" : "类别分布" }}
            </strong>
          </div>
        </div>

        <div v-if="workspace.distributionResult.has_more" class="groupby-note subtle">
          <strong>结果已截断</strong>
          <span>当前仅显示前 {{ workspace.distributionResult.limit }} 组，可以调大结果上限查看更多。</span>
        </div>

        <div v-if="workspace.distributionResult.chart?.categories?.length" class="distribution-chart-panel">
          <div class="chart-meta">
            <span class="badge badge-success">{{ workspace.distributionResult.column }}</span>
            <span class="badge badge-primary">
              {{ workspace.distributionResult.resolved_mode === "numeric" ? "数值分箱" : "类别分布" }}
            </span>
            <span
              v-if="workspace.distributionResult.include_cumulative"
              class="badge badge-primary"
            >
              含累计频率
            </span>
          </div>
          <div
            :ref="(el) => (workspace.distributionChartRef = el)"
            class="distribution-chart-box"
          ></div>
        </div>

        <div v-if="workspace.distributionRows.length" class="table-shell distribution-table-shell">
          <table class="data-table">
            <thead>
              <tr>
                <th>区间 / 类别</th>
                <th>频数</th>
                <th>占比</th>
                <th v-if="workspace.distributionResult.include_cumulative">累计频数</th>
                <th v-if="workspace.distributionResult.include_cumulative">累计占比</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(row, index) in workspace.distributionRows"
                :key="`${row.bucket}-${index}`"
              >
                <td>{{ row.bucket }}</td>
                <td>{{ row.count }}</td>
                <td>{{ workspace.formatPercent(row.percentage) }}</td>
                <td v-if="workspace.distributionResult.include_cumulative">{{ row.cumulative_count }}</td>
                <td v-if="workspace.distributionResult.include_cumulative">
                  {{ workspace.formatPercent(row.cumulative_percentage) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <div v-else class="empty-state">
        <strong>还没有频数分布结果</strong>
        <span>先选择字段，再执行频数分布分析，系统会展示频数表和分布图。</span>
      </div>
    </div>
  </section>
</template>

<script setup>
import { inject } from "vue";

const workspace = inject("workspaceCtx");
</script>
