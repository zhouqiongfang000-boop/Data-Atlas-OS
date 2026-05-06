import {
  computed,
  defineComponent,
  nextTick,
  onBeforeUnmount,
  onMounted,
  provide,
  proxyRefs,
  ref,
  watch,
} from "vue";
import { useRoute, useRouter } from "vue-router";

import api from "../../api";
import WorkspaceAiAssistantDock from "../../components/workspace/WorkspaceAiAssistantDock.vue";
import WorkspaceAssetsSection from "../../components/workspace/WorkspaceAssetsSection.vue";
import WorkspaceExplorationSection from "../../components/workspace/WorkspaceExplorationSection.vue";
import WorkspaceOverviewSection from "../../components/workspace/WorkspaceOverviewSection.vue";
import WorkspacePreparationSection from "../../components/workspace/WorkspacePreparationSection.vue";
import WorkspaceSectionBar from "../../components/workspace/WorkspaceSectionBar.vue";
import WorkspaceSidebar from "../../components/workspace/WorkspaceSidebar.vue";
import WorkspaceVisualizationSection from "../../components/workspace/WorkspaceVisualizationSection.vue";

let echartsLoader = null;

const MAX_UPLOAD_SIZE = 50 * 1024 * 1024;

const getEcharts = async () => {
  if (!echartsLoader) {
    echartsLoader = import("echarts");
  }
  return echartsLoader;
};

const waitForAnimationFrame = () =>
  new Promise((resolve) => {
    window.requestAnimationFrame(() => resolve());
  });

const NUMERIC_CHART_OPTIONS = [
  { value: "histogram", label: "直方图" },
  { value: "line", label: "折线图" },
  { value: "area", label: "面积图" },
  { value: "bar", label: "柱状图" },
  { value: "scatter", label: "散点图" },
  { value: "boxplot", label: "箱线图" },
];

const CATEGORICAL_CHART_OPTIONS = [
  { value: "bar", label: "柱状图" },
  { value: "horizontal_bar", label: "横向柱图" },
  { value: "pie", label: "饼图" },
  { value: "donut", label: "环形图" },
  { value: "rose", label: "玫瑰图" },
  { value: "treemap", label: "树图" },
];

const CHART_TYPE_LABELS = {
  histogram: "直方图",
  line: "折线图",
  area: "面积图",
  bar: "柱状图",
  scatter: "散点图",
  boxplot: "箱线图",
  horizontal_bar: "横向柱图",
  pie: "饼图",
  donut: "环形图",
  rose: "玫瑰图",
  treemap: "树图",
};

const CLEANING_MISSING_OPTIONS = [
  { value: "none", label: "暂不处理" },
  { value: "drop_rows", label: "删除含缺失值的行" },
  { value: "fill_median_mode", label: "智能填充（中位数/众数）" },
  { value: "fill_fixed", label: "使用固定值填充" },
];

const CLEANING_OUTLIER_OPTIONS = [
  { value: "none", label: "仅检测，不处理" },
  { value: "drop_iqr_rows", label: "按统计规则删除候选异常所在行" },
];

const TYPE_CONVERSION_OPTIONS = [
  { value: "numeric", label: "转为数值" },
  { value: "datetime", label: "转为日期时间" },
  { value: "text", label: "转为文本" },
];

const QUERY_OPERATOR_OPTIONS = [
  { value: "eq", label: "等于" },
  { value: "ne", label: "不等于" },
  { value: "gt", label: "大于" },
  { value: "gte", label: "大于等于" },
  { value: "lt", label: "小于" },
  { value: "lte", label: "小于等于" },
  { value: "contains", label: "包含" },
  { value: "in", label: "属于集合" },
  { value: "between", label: "介于区间" },
  { value: "is_null", label: "为空" },
  { value: "not_null", label: "不为空" },
];

const QUERY_SORT_DIRECTION_OPTIONS = [
  { value: "asc", label: "升序" },
  { value: "desc", label: "降序" },
];

const GROUP_AGGREGATION_OPTIONS = [
  { value: "count", label: "计数" },
  { value: "sum", label: "求和" },
  { value: "mean", label: "平均值" },
  { value: "min", label: "最小值" },
  { value: "max", label: "最大值" },
  { value: "median", label: "中位数" },
];

const CORRELATION_VIEW_OPTIONS = [
  { value: "heatmap", label: "热力图" },
  { value: "table", label: "矩阵表" },
];

const CORRELATION_THRESHOLD_OPTIONS = [
  { value: 0, label: "全部" },
  { value: 0.3, label: "|r| ≥ 0.3" },
  { value: 0.5, label: "|r| ≥ 0.5" },
  { value: 0.7, label: "|r| ≥ 0.7" },
];

const DISTRIBUTION_MODE_OPTIONS = [
  { value: "auto", label: "自动判断" },
  { value: "categorical", label: "类别分布" },
  { value: "numeric", label: "数值分箱" },
];

const DISTRIBUTION_SORT_OPTIONS = [
  { value: "default", label: "默认顺序" },
  { value: "frequency_desc", label: "按频数降序" },
];

const FIELD_PROFILE_TYPE_OPTIONS = [
  { value: "all", label: "全部字段" },
  { value: "numeric", label: "数值" },
  { value: "categorical", label: "类别" },
  { value: "datetime", label: "日期时间" },
  { value: "empty", label: "空列" },
];

const WORKSPACE_SECTION_OPTIONS = [
  { value: "overview", label: "概览", description: "预览与字段画像" },
  { value: "preparation", label: "数据准备", description: "清洗与回滚" },
  { value: "exploration", label: "分析探索", description: "查询、分组与分布" },
  { value: "visualization", label: "可视化", description: "图表、统计与相关性" },
  { value: "assets", label: "资产中心", description: "AI 与分析记录" },
];

const AI_QUICK_PROMPTS = [
  "请概括这份数据的整体情况",
  "推荐我下一步最值得做的分析",
  "哪些字段最适合可视化展示",
];

const AI_MESSAGE_MODE_LABELS = {
  question: "自由提问",
  explain: "结果解读",
  presentation: "展示摘要",
};

const WORKSPACE_SECTION_STICKY_TOP = 16;

const AI_CONTEXTUAL_PROMPT_MAP = {
  overview: [
    "帮我快速读懂这份数据的字段结构",
    "哪些字段最值得优先关注",
  ],
  preparation: [
    "这份数据现在还有哪些质量风险",
    "下一步最适合做哪种清洗处理",
  ],
  exploration: [
    "我现在最适合先做哪种分析",
    "哪些字段适合做分组统计或分布分析",
  ],
  visualization: [
    "哪些字段最适合可视化展示",
    "推荐我一条适合展示的图表分析路径",
  ],
  assets: [
    "请概括这份数据的整体情况",
    "帮我生成一段适合展示的分析摘要",
  ],
};

const PANEL_HELP_CONTENT = {
  overview: {
    title: "看当前进度",
    body: "这里会显示你当前正在分析哪份文件、停在哪个字段和图表类型，方便快速接上工作。",
  },
  upload: {
    title: "上传入口",
    body: "先上传 CSV 数据文件，系统会把它加入文件列表，后面的预览、清洗和分析都会基于它展开。",
  },
  files: {
    title: "切换数据源",
    body: "这里保存你的数据文件。点击文件就能切换分析对象，删除会把这份文件从工作区移除。",
  },
  plans: {
    title: "保存你的分析配置",
    body: "把当前文件下的筛选、分组、分布、热力图和图表设置保存下来，下次可以一键恢复继续分析。",
  },
  preview: {
    title: "先看数据长什么样",
    body: "先浏览前几行，确认字段名、格式和内容是否正常，再决定怎么清洗和分析。",
  },
  dictionary: {
    title: "看清每个字段能做什么",
    body: "这里会整理字段类型、缺失率、唯一值、样本值和推荐分析方向，帮助非专业用户快速理解每一列的用途。",
  },
  cleaning: {
    title: "先检查再清洗",
    body: "这里会检查缺失值、重复值和统计异常候选。注意异常候选不等于错误数据，只是提醒你关注极端值。",
  },
  cleaningHistory: {
    title: "看清洗链路，再决定要不要回退",
    body: "这里会记录当前文件是怎么一步步清洗出来的，也能快速切回处理前文件，或基于某个历史节点生成回滚文件。",
  },
  query: {
    title: "先圈定分析范围",
    body: "用条件筛选、排序和分页先找到你真正关心的数据，后面的分组统计会自动复用这些条件。",
  },
  groupby: {
    title: "按类别汇总结果",
    body: "主分组字段决定先按什么分类，次分组字段是在每个主组里再细分；统计字段会算出每组的计数、均值、最大值等结果。",
  },
  distribution: {
    title: "看字段的分布情况",
    body: "它会告诉你某个值或某个区间出现了多少次、占了多少比例，适合看类别占比和数值集中区间。",
  },
  chart: {
    title: "把结果画出来",
    body: "选择字段后生成合适的图形，用更直观的方式看趋势、分布和类别占比。",
  },
  stats: {
    title: "看整体特征",
    body: "这里会自动汇总均值、标准差、四分位数等指标，适合先把整份数据的轮廓看清楚。",
  },
  correlation: {
    title: "看字段之间有没有关系",
    body: "相关系数越接近 1 或 -1，说明两个数值字段的变化关系越明显；越接近 0，关系越弱。",
  },
  predict: {
    title: "预测未来趋势",
    body: "选择一个数值目标字段，系统会用线性回归从历史序列中学习趋势，并生成未来若干步预测和趋势图。",
  },
  assistant: {
    title: "AI 分析助手",
    body: "你可以直接提问，AI 会结合当前文件的字段画像、质量报告和基础分析结果，给出解释、提醒和下一步建议。",
  },
  history: {
    title: "回看分析过程",
    body: "这里会记录你生成过的图表分析，方便回顾展示路径和结果。",
  },
};

export default defineComponent({
  name: "HomeView",
  components: {
    WorkspaceAiAssistantDock,
    WorkspaceAssetsSection,
    WorkspaceExplorationSection,
    WorkspaceOverviewSection,
    WorkspacePreparationSection,
    WorkspaceSectionBar,
    WorkspaceSidebar,
    WorkspaceVisualizationSection,
  },
  setup() {
    const route = useRoute();
    const router = useRouter();
    const activeWorkspaceSection = ref("overview");

    const files = ref([]);
    const selectedFile = ref("");
    const previewColumns = ref([]);
    const previewData = ref([]);
    const analysis = ref(null);
    const chartData = ref(null);
    const distributionResult = ref(null);
    const predictionResult = ref(null);
    const currentColumn = ref("");
    const chartRef = ref(null);
    const distributionChartRef = ref(null);
    const correlationChartRef = ref(null);
    const predictionChartRef = ref(null);

    const loadingFiles = ref(false);
    const loadingPreview = ref(false);
    const loadingAnalysis = ref(false);
    const loadingChart = ref(false);
    const loadingDistribution = ref(false);
    const loadingPrediction = ref(false);

    const feedbackText = ref("");
    const feedbackType = ref("success");
    const currentChartType = ref("");
    const showChartExportPanel = ref(false);
    const chartExportForm = ref({
      title: "",
      xAxisLabel: "",
      yAxisLabel: "",
    });

    const currentUser = ref(null);
    const aiStatus = ref({
      enabled: false,
      provider: "",
      model: "",
      message: "",
    });
    const showAiAssistantDrawer = ref(false);
    const aiAssistantStage = ref("idle");
    const aiAssistantLastError = ref("");
    const aiAssistantLastCompletedAt = ref("");
    const aiAssistantForm = ref({
      question: "",
    });
    const aiAssistantMessages = ref([]);
    const loadingAiAssistant = ref(false);
    const historyRecords = ref([]);
    const analysisPlans = ref([]);
    const dashboardSummary = ref({
      file_count: 0,
      history_count: 0,
      latest_file: null,
    });
    const qualityReport = ref(null);
    const loadingQuality = ref(false);
    const fieldProfileReport = ref(null);
    const loadingFieldProfiles = ref(false);
    const cleaningHistory = ref({
      current_file: null,
      lineage: [],
      descendants: [],
      can_rollback: false,
    });
    const loadingCleaningHistory = ref(false);
    const rollingBackHistoryId = ref(null);
    const groupByResult = ref(null);
    const loadingGroupBy = ref(false);
    const cleaningPreview = ref(null);
    const loadingCleaningPreview = ref(false);
    const applyingCleaning = ref(false);
    const queryPreviewResult = ref(null);
    const loadingQueryPreview = ref(false);
    const expandedOutlierColumn = ref("");
    const loadingOutlierColumn = ref("");
    const outlierDetailMap = ref({});
    const openPanelHelpKey = ref("");
    const correlationView = ref("heatmap");
    const correlationAbsThreshold = ref(0);
    const exportingTarget = ref("");
    const loadingPlans = ref(false);
    const savingPlan = ref(false);
    const applyingPlanId = ref(null);
    const deletingPlanId = ref(null);
    const planForm = ref({
      name: "",
    });
    const fieldDictionaryForm = ref({
      search: "",
      type: "all",
    });
    const queryForm = ref({
      filterColumn: "",
      filterOperator: "eq",
      filterValue: "",
      filterSecondValue: "",
      filters: [],
      sortColumn: "",
      sortDirection: "asc",
      limit: 20,
      offset: 0,
    });
    const groupByForm = ref({
      primaryGroupColumn: "",
      secondaryGroupColumn: "",
      metricColumn: "",
      metricAggregation: "count",
      metrics: [],
      limit: 20,
    });
    const distributionForm = ref({
      column: "",
      mode: "auto",
      bins: 8,
      includeCumulative: true,
      sortMode: "default",
      limit: 20,
    });
    const predictionForm = ref({
      targetColumn: "",
      featureColumn: "",
      periods: 6,
    });
    const cleaningForm = ref({
      missingStrategy: "none",
      fillValue: "",
      removeDuplicates: false,
      outlierStrategy: "none",
      conversionColumn: "",
      conversionTargetType: "numeric",
      typeConversions: [],
    });

    const normalizeWorkspaceSection = (section) => {
      return WORKSPACE_SECTION_OPTIONS.some((item) => item.value === section)
        ? section
        : "overview";
    };

    const syncWorkspaceSectionFromRoute = (section) => {
      activeWorkspaceSection.value = normalizeWorkspaceSection(section);
    };

    const setWorkspaceSection = (section) => {
      const normalizedSection = normalizeWorkspaceSection(section);
      activeWorkspaceSection.value = normalizedSection;

      if (route.query.section !== normalizedSection) {
        router.replace({
          path: route.path,
          query: {
            ...route.query,
            section: normalizedSection,
          },
        });
      }
    };

    syncWorkspaceSectionFromRoute(route.query.section);

    watch(
      () => route.query.section,
      (section) => {
        syncWorkspaceSectionFromRoute(section);
      }
    );

    let chartInstance = null;
    let distributionChartInstance = null;
    let correlationChartInstance = null;
    let predictionChartInstance = null;

    const selectedFileDisplay = computed(() => {
      if (!selectedFile.value) return "";
      return formatDisplayName(selectedFile.value);
    });

    const aiContextualPrompts = computed(() => {
      const contextual = AI_CONTEXTUAL_PROMPT_MAP[activeWorkspaceSection.value] || [];
      return Array.from(new Set([...contextual, ...AI_QUICK_PROMPTS])).slice(0, 6);
    });

    const latestAiAssistantMessage = computed(() => {
      for (let index = aiAssistantMessages.value.length - 1; index >= 0; index -= 1) {
        const item = aiAssistantMessages.value[index];
        if (item?.role === "assistant") return item;
      }
      return null;
    });

    const latestAiPresentationMessage = computed(() => {
      for (let index = aiAssistantMessages.value.length - 1; index >= 0; index -= 1) {
        const item = aiAssistantMessages.value[index];
        if (item?.role === "assistant" && item.mode === "presentation") return item;
      }
      return null;
    });

    const getColumnKind = (column) => {
      if (!column || !analysis.value) return "";
      if (analysis.value.numeric_columns?.includes(column)) return "numeric";
      if (analysis.value.categorical_columns?.includes(column)) return "categorical";
      return "";
    };

    const getDefaultChartType = (column) => {
      return getColumnKind(column) === "categorical" ? "bar" : "histogram";
    };

    const currentColumnKind = computed(() => getColumnKind(currentColumn.value));

    const currentColumnKindLabel = computed(() => {
      if (currentColumnKind.value === "numeric") return "数值字段";
      if (currentColumnKind.value === "categorical") return "类别字段";
      return "未选择字段";
    });

    const currentChartOptions = computed(() => {
      if (currentColumnKind.value === "categorical") {
        return CATEGORICAL_CHART_OPTIONS;
      }
      if (currentColumnKind.value === "numeric") {
        return NUMERIC_CHART_OPTIONS;
      }
      return [];
    });

    const currentChartTypeLabel = computed(() => {
      return CHART_TYPE_LABELS[currentChartType.value] || "未生成图表";
    });

    const qualityColumns = computed(() => qualityReport.value?.columns || []);
    const fieldProfiles = computed(() => fieldProfileReport.value?.profiles || []);
    const fieldProfileTypeCounts = computed(
      () =>
        fieldProfileReport.value?.type_counts || {
          numeric: 0,
          categorical: 0,
          datetime: 0,
          empty: 0,
        }
    );
    const filteredFieldProfiles = computed(() => {
      const keyword = fieldDictionaryForm.value.search.trim().toLowerCase();
      const selectedType = fieldDictionaryForm.value.type;

      return fieldProfiles.value.filter((item) => {
        const matchesType =
          selectedType === "all" || item.detected_type === selectedType;
        const matchesKeyword =
          !keyword ||
          item.name.toLowerCase().includes(keyword) ||
          item.dtype.toLowerCase().includes(keyword) ||
          (item.role_hint || "").toLowerCase().includes(keyword);
        return matchesType && matchesKeyword;
      });
    });
    const availableQueryColumns = computed(
      () => analysis.value?.columns || previewColumns.value || []
    );
    const availableGroupColumns = computed(() => availableQueryColumns.value);
    const availableGroupMetricColumns = computed(() => availableQueryColumns.value);
    const availableDistributionColumns = computed(() => availableQueryColumns.value);
    const availablePredictionTargetColumns = computed(
      () => analysis.value?.numeric_columns || []
    );
    const availablePredictionFeatureColumns = computed(() =>
      availableQueryColumns.value.filter(
        (column) => column !== predictionForm.value.targetColumn
      )
    );
    const availableConversionColumns = computed(() =>
      qualityColumns.value.map((column) => column.name)
    );
    const cleaningPreviewColumns = computed(
      () => cleaningPreview.value?.columns || []
    );
    const cleaningPreviewRows = computed(() => cleaningPreview.value?.data || []);
    const queryPreviewColumns = computed(
      () => queryPreviewResult.value?.columns || []
    );
    const queryPreviewRows = computed(() => queryPreviewResult.value?.data || []);
    const groupByColumns = computed(() => groupByResult.value?.columns || []);
    const groupByRows = computed(() => groupByResult.value?.data || []);
    const distributionRows = computed(() => distributionResult.value?.rows || []);
    const correlationColumns = computed(
      () => analysis.value?.numeric_columns || []
    );
    const correlationHeatmapData = computed(() => {
      if (!analysis.value?.correlation || !correlationColumns.value.length) {
        return [];
      }

      return correlationColumns.value.flatMap((rowName, rowIndex) =>
        correlationColumns.value.map((columnName, columnIndex) => {
          const rawValue = analysis.value?.correlation?.[rowName]?.[columnName];
          const value = Number(rawValue);
          const normalizedValue = Number.isFinite(value)
            ? Number(value.toFixed(4))
            : null;
          const absoluteValue =
            normalizedValue === null ? null : Math.abs(normalizedValue);
          const passesThreshold =
            rowIndex === columnIndex ||
            absoluteValue === null ||
            absoluteValue >= correlationAbsThreshold.value;

          return [
            columnIndex,
            rowIndex,
            passesThreshold ? normalizedValue : null,
          ];
        })
      );
    });
    const visibleCorrelationPairCount = computed(() => {
      if (!correlationHeatmapData.value.length || !correlationColumns.value.length) {
        return 0;
      }

      return correlationHeatmapData.value.filter(([x, y, value]) => {
        return x < y && value !== null && value !== undefined;
      }).length;
    });
    const correlationChartHeight = computed(() => {
      const fieldCount = correlationColumns.value.length;
      const nextHeight = fieldCount * 34 + 170;
      return `${Math.max(360, Math.min(nextHeight, 760))}px`;
    });
    const shouldShowDistributionBins = computed(() => {
      if (distributionForm.value.mode === "numeric") return true;
      if (distributionForm.value.mode === "categorical") return false;
      return getColumnKind(distributionForm.value.column) === "numeric";
    });

    const chartPanelSubtitle = computed(() => {
      if (currentColumnKind.value === "categorical") {
        return "支持类别字段分布图、环形图、玫瑰图和树图";
      }
      if (currentColumnKind.value === "numeric") {
        return "支持趋势图、分布图、散点图和箱线图";
      }
      return "先选择字段，再选择图表类型生成可视化";
    });

    const sanitizeDownloadStem = (value, fallback = "chart") => {
      const normalized = String(value || "")
        .replace(/[\\/:*?"<>|]+/g, " ")
        .replace(/\s+/g, " ")
        .trim();
      return normalized || fallback;
    };

    const generatedChartPresentation = computed(() => {
      if (!chartData.value) {
        return {
          title: "",
          xAxisLabel: "",
          yAxisLabel: "",
          usesCartesianAxes: false,
          primaryLabelName: "\u6a2a\u8f74",
          secondaryLabelName: "\u7eb5\u8f74",
        };
      }

      const resolvedType =
        chartData.value.resolved_type ||
        currentChartType.value ||
        chartData.value.type ||
        "";
      const isHorizontal = chartData.value.orientation === "horizontal";
      const usesCartesianAxes =
        chartData.value.type !== "pie" && chartData.value.type !== "treemap";
      const backendTitle = String(chartData.value.title || "").trim();
      const defaultTitle =
        backendTitle ||
        [selectedFileDisplay.value, currentColumn.value, currentChartTypeLabel.value]
          .filter(Boolean)
          .join(" · ") ||
        "\u56fe\u8868\u5bfc\u51fa";

      let primaryLabelName = "\u6a2a\u8f74";
      let secondaryLabelName = "\u7eb5\u8f74";
      let xAxisLabel = "";
      let yAxisLabel = "";

      if (!usesCartesianAxes) {
        primaryLabelName = "\u5206\u7c7b\u7ef4\u5ea6";
        secondaryLabelName = "\u7edf\u8ba1\u53e3\u5f84";
        xAxisLabel = currentColumn.value || "\u5206\u7c7b\u9879";
        yAxisLabel = "\u5360\u6bd4 / \u9891\u6570";
      } else if (resolvedType === "histogram") {
        xAxisLabel = `${currentColumn.value || "\u6570\u503c"}\u533a\u95f4`;
        yAxisLabel = "\u9891\u6570";
      } else if (resolvedType === "boxplot") {
        xAxisLabel = "\u5b57\u6bb5";
        yAxisLabel = `${currentColumn.value || "\u6570\u503c"}\u5206\u5e03`;
      } else if (chartData.value.column_kind === "categorical") {
        if (isHorizontal) {
          xAxisLabel = "\u9891\u6570";
          yAxisLabel = currentColumn.value || "\u5206\u7c7b";
        } else {
          xAxisLabel = currentColumn.value || "\u5206\u7c7b";
          yAxisLabel = "\u9891\u6570";
        }
      } else {
        xAxisLabel = "\u8bb0\u5f55\u987a\u5e8f";
        yAxisLabel = currentColumn.value || "\u6570\u503c";
      }

      return {
        title: defaultTitle,
        xAxisLabel,
        yAxisLabel,
        usesCartesianAxes,
        primaryLabelName,
        secondaryLabelName,
      };
    });

    const activeChartPresentation = computed(() => {
      const generated = generatedChartPresentation.value;
      if (!showChartExportPanel.value) return generated;

      return {
        ...generated,
        title: chartExportForm.value.title.trim() || generated.title,
        xAxisLabel: generated.usesCartesianAxes
          ? chartExportForm.value.xAxisLabel.trim() || generated.xAxisLabel
          : generated.xAxisLabel,
        yAxisLabel: generated.usesCartesianAxes
          ? chartExportForm.value.yAxisLabel.trim() || generated.yAxisLabel
          : generated.yAxisLabel,
      };
    });

    const togglePanelHelp = (panelKey) => {
      openPanelHelpKey.value =
        openPanelHelpKey.value === panelKey ? "" : panelKey;
    };

    const isPanelHelpOpen = (panelKey) => openPanelHelpKey.value === panelKey;

    const getCorrelationStrengthLabel = (value) => {
      const absoluteValue = Math.abs(Number(value));

      if (!Number.isFinite(absoluteValue)) return "无有效值";
      if (absoluteValue >= 0.8) return "极强相关";
      if (absoluteValue >= 0.6) return "强相关";
      if (absoluteValue >= 0.4) return "中等相关";
      if (absoluteValue >= 0.2) return "弱相关";
      return "很弱相关";
    };

    const setCorrelationView = async (view) => {
      correlationView.value = view;

      if (view === "heatmap") {
        await nextTick();
        await renderCorrelationHeatmap();
        return;
      }

      clearCorrelationChartInstance();
    };

    const setCorrelationAbsThreshold = async (threshold) => {
      correlationAbsThreshold.value = threshold;

      if (correlationView.value === "heatmap") {
        await nextTick();
        await renderCorrelationHeatmap();
      }
    };

    const normalizeGroupAggregations = (aggregations = []) => {
      const selectedSource = Array.isArray(aggregations)
        ? aggregations
        : [aggregations];
      const selected = GROUP_AGGREGATION_OPTIONS.map((option) => option.value).filter(
        (value) => selectedSource.includes(value)
      );
      return selected.length ? selected : ["count"];
    };

    const mergeGroupMetric = (metricList, metricColumn, aggregations) => {
      const normalizedAggregations = normalizeGroupAggregations(aggregations);
      const existingIndex = metricList.findIndex(
        (item) => item.column === metricColumn
      );

      if (existingIndex === -1) {
        return {
          metrics: [
            ...metricList,
            {
              column: metricColumn,
              aggregations: normalizedAggregations,
            },
          ],
          merged: false,
        };
      }

      const mergedAggregations = GROUP_AGGREGATION_OPTIONS.map(
        (option) => option.value
      ).filter(
        (value) =>
          metricList[existingIndex].aggregations.includes(value) ||
          normalizedAggregations.includes(value)
      );

      const nextMetrics = [...metricList];
      nextMetrics[existingIndex] = {
        ...nextMetrics[existingIndex],
        aggregations: mergedAggregations,
      };

      return {
        metrics: nextMetrics,
        merged: true,
      };
    };

    const setMissingStrategy = (value) => {
      cleaningForm.value.missingStrategy = value;
    };

    const setOutlierStrategy = (value) => {
      cleaningForm.value.outlierStrategy = value;
    };

    const resetQueryState = () => {
      queryPreviewResult.value = null;
      queryForm.value = {
        filterColumn: "",
        filterOperator: "eq",
        filterValue: "",
        filterSecondValue: "",
        filters: [],
        sortColumn: "",
        sortDirection: "asc",
        limit: 20,
        offset: 0,
      };
    };

    const resetGroupByState = () => {
      groupByResult.value = null;
      groupByForm.value = {
        primaryGroupColumn: "",
        secondaryGroupColumn: "",
        metricColumn: "",
        metricAggregation: "count",
        metrics: [],
        limit: 20,
      };
    };

    const queryOperatorNeedsValue = (operator) => {
      return !["is_null", "not_null"].includes(operator);
    };

    const queryOperatorNeedsSecondValue = (operator) => operator === "between";

    const addQueryFilter = () => {
      const { filterColumn, filterOperator, filterValue, filterSecondValue } =
        queryForm.value;

      if (!filterColumn) {
        feedbackText.value = "请先选择筛选字段";
        feedbackType.value = "warning";
        return;
      }

      if (queryOperatorNeedsValue(filterOperator) && !String(filterValue).trim()) {
        feedbackText.value = "请先输入筛选条件";
        feedbackType.value = "warning";
        return;
      }

      if (
        queryOperatorNeedsSecondValue(filterOperator) &&
        !String(filterSecondValue).trim()
      ) {
        feedbackText.value = "请补充区间的第二个值";
        feedbackType.value = "warning";
        return;
      }

      queryForm.value.filters = [
        ...queryForm.value.filters,
        {
          column: filterColumn,
          operator: filterOperator,
          value: filterValue,
          secondValue: filterSecondValue,
        },
      ];
      queryForm.value.filterColumn = "";
      queryForm.value.filterOperator = "eq";
      queryForm.value.filterValue = "";
      queryForm.value.filterSecondValue = "";
      feedbackText.value = "";
    };

    const removeQueryFilter = (index) => {
      queryForm.value.filters = queryForm.value.filters.filter(
        (_, filterIndex) => filterIndex !== index
      );
    };

    const setGroupAggregation = (aggregation) => {
      groupByForm.value.metricAggregation = aggregation;
    };

    const addGroupMetric = () => {
      const metricColumn = groupByForm.value.metricColumn;
      const aggregation = groupByForm.value.metricAggregation;

      if (!metricColumn) {
        feedbackText.value = "请先选择统计字段";
        feedbackType.value = "warning";
        return;
      }

      const { metrics, merged } = mergeGroupMetric(
        groupByForm.value.metrics,
        metricColumn,
        aggregation
      );

      groupByForm.value.metrics = metrics;
      groupByForm.value.metricColumn = "";
      groupByForm.value.metricAggregation = "count";
      feedbackText.value = merged ? "已更新这个统计字段的聚合方式" : "统计字段已添加";
      feedbackType.value = "success";
    };

    const removeGroupMetric = (column) => {
      groupByForm.value.metrics = groupByForm.value.metrics.filter(
        (item) => item.column !== column
      );
    };

    const addTypeConversion = () => {
      const column = cleaningForm.value.conversionColumn;
      const targetType = cleaningForm.value.conversionTargetType;

      if (!column) {
        feedbackText.value = "请先选择需要转换的字段";
        feedbackType.value = "warning";
        return;
      }

      if (
        cleaningForm.value.typeConversions.some((item) => item.column === column)
      ) {
        feedbackText.value = "该字段已经设置过类型转换";
        feedbackType.value = "warning";
        return;
      }

      cleaningForm.value.typeConversions = [
        ...cleaningForm.value.typeConversions,
        { column, targetType },
      ];
      cleaningForm.value.conversionColumn = "";
      feedbackText.value = "";
    };

    const removeTypeConversion = (column) => {
      cleaningForm.value.typeConversions = cleaningForm.value.typeConversions.filter(
        (item) => item.column !== column
      );
    };

    const formatOutlierColumnLabel = (columnName) => {
      return columnName === "_row_number" ? "原始行号" : columnName;
    };

    const resetCleaningState = () => {
      qualityReport.value = null;
      fieldProfileReport.value = null;
      cleaningHistory.value = {
        current_file: null,
        lineage: [],
        descendants: [],
        can_rollback: false,
      };
      cleaningPreview.value = null;
      expandedOutlierColumn.value = "";
      loadingOutlierColumn.value = "";
      outlierDetailMap.value = {};
      rollingBackHistoryId.value = null;
      cleaningForm.value = {
        missingStrategy: "none",
        fillValue: "",
        removeDuplicates: false,
        outlierStrategy: "none",
        conversionColumn: "",
        conversionTargetType: "numeric",
        typeConversions: [],
      };
      fieldDictionaryForm.value = {
        search: "",
        type: "all",
      };
    };

    const resetChartExportState = () => {
      showChartExportPanel.value = false;
      chartExportForm.value = {
        title: "",
        xAxisLabel: "",
        yAxisLabel: "",
      };
    };

    const clearChartInstance = () => {
      if (chartInstance) {
        chartInstance.dispose();
        chartInstance = null;
      }
    };

    const clearDistributionChartInstance = () => {
      if (distributionChartInstance) {
        distributionChartInstance.dispose();
        distributionChartInstance = null;
      }
    };

    const clearCorrelationChartInstance = () => {
      if (correlationChartInstance) {
        correlationChartInstance.dispose();
        correlationChartInstance = null;
      }
    };

    const clearPredictionChartInstance = () => {
      if (predictionChartInstance) {
        predictionChartInstance.dispose();
        predictionChartInstance = null;
      }
    };

    const resetDistributionState = () => {
      clearDistributionChartInstance();
      distributionResult.value = null;
      distributionForm.value = {
        column: "",
        mode: "auto",
        bins: 8,
        includeCumulative: true,
        sortMode: "default",
        limit: 20,
      };
    };

    const resetPredictionState = () => {
      clearPredictionChartInstance();
      predictionResult.value = null;
      predictionForm.value = {
        targetColumn: "",
        featureColumn: "",
        periods: 6,
      };
    };

    const resetPlanState = () => {
      analysisPlans.value = [];
      planForm.value = {
        name: "",
      };
      applyingPlanId.value = null;
      deletingPlanId.value = null;
    };

    const resetAiAssistantState = (preserveStatus = true) => {
      aiAssistantForm.value = {
        question: "",
      };
      aiAssistantMessages.value = [];
      loadingAiAssistant.value = false;
      aiAssistantStage.value = "idle";
      aiAssistantLastError.value = "";
      aiAssistantLastCompletedAt.value = "";

      if (!preserveStatus) {
        aiStatus.value = {
          enabled: false,
          provider: "",
          model: "",
          message: "",
        };
      }
    };

    const openAiAssistantDrawer = (question = "") => {
      showAiAssistantDrawer.value = true;
      if (question) {
        aiAssistantForm.value.question = question;
      }
    };

    const closeAiAssistantDrawer = () => {
      showAiAssistantDrawer.value = false;
    };

    const toggleAiAssistantDrawer = () => {
      showAiAssistantDrawer.value = !showAiAssistantDrawer.value;
    };

    const getAiErrorMessage = (error) => {
      const detail = error?.response?.data?.detail;
      const normalizedDetail = typeof detail === "string" ? detail : "";

      if (error?.code === "ECONNABORTED") {
        return "AI 分析耗时较长，本次请求已超时。你可以稍后重试，或先缩小问题范围。";
      }

      if (error?.response?.status === 503) {
        return normalizedDetail || "AI 助手尚未配置完成，请先检查后端的模型配置。";
      }

      if (error?.response?.status === 502) {
        return normalizedDetail || "AI 提供商调用失败，请稍后重试。";
      }

      if (error?.response?.status === 401) {
        return "当前登录状态已失效，请重新登录后再试。";
      }

      if (normalizedDetail) {
        return normalizedDetail;
      }

      if (error?.message) {
        return `AI 助手暂时无法完成本次分析：${error.message}`;
      }

      return "AI 助手暂时无法完成本次分析，请稍后再试。";
    };

    const copyAiMessageContent = async (message) => {
      if (!message?.content) return;

      try {
        await navigator.clipboard.writeText(message.content);
        feedbackText.value = "AI 内容已复制";
        feedbackType.value = "success";
      } catch (error) {
        feedbackText.value = "复制失败，请稍后再试";
        feedbackType.value = "error";
      }
    };

    const resetSelectedFileState = () => {
      clearChartInstance();
      clearDistributionChartInstance();
      clearCorrelationChartInstance();
      clearPredictionChartInstance();
      resetChartExportState();
      selectedFile.value = "";
      previewColumns.value = [];
      previewData.value = [];
      analysis.value = null;
      chartData.value = null;
      distributionResult.value = null;
      predictionResult.value = null;
      currentColumn.value = "";
      currentChartType.value = "";
      resetCleaningState();
      resetQueryState();
      resetGroupByState();
      resetDistributionState();
      resetPredictionState();
      resetPlanState();
      resetAiAssistantState();
    };

    const fetchMe = async () => {
      try {
        const res = await api.get("/me");
        currentUser.value = res.data;
      } catch (error) {
        console.error("获取用户信息失败:", error);
      }
    };

    const fetchAiStatus = async () => {
      try {
        const res = await api.get("/ai/status");
        aiStatus.value = {
          enabled: Boolean(res.data?.enabled),
          provider: res.data?.provider || "",
          model: res.data?.model || "",
          message: res.data?.message || "",
        };
      } catch (error) {
        aiStatus.value = {
          enabled: false,
          provider: "",
          model: "",
          message: "unavailable",
        };
      }
    };

    const fetchFiles = async (autoSelect = true) => {
      loadingFiles.value = true;

      try {
        const res = await api.get("/files");
        files.value = res.data.files || [];

        if (!files.value.length) {
          resetSelectedFileState();
          return;
        }

        const currentStillExists = files.value.some(
          (item) => item.name === selectedFile.value
        );

        if (autoSelect && (!selectedFile.value || !currentStillExists)) {
          await selectFile(files.value[0].name);
        }
      } catch (error) {
        feedbackText.value = "获取文件列表失败";
        feedbackType.value = "error";
        clearCorrelationChartInstance();
      } finally {
        loadingFiles.value = false;
      }
    };

    const fetchHistory = async () => {
      try {
        const res = await api.get("/history?limit=8");
        historyRecords.value = res.data.records || [];
      } catch (error) {
        console.error("获取历史记录失败:", error);
      }
    };

    const fetchAnalysisPlans = async (filename = selectedFile.value) => {
      if (!filename) {
        analysisPlans.value = [];
        return;
      }

      loadingPlans.value = true;
      try {
        const res = await api.get(
          `/plans?filename=${encodeURIComponent(filename)}`
        );
        analysisPlans.value = res.data.plans || [];
      } catch (error) {
        console.error("获取分析方案失败:", error);
      } finally {
        loadingPlans.value = false;
      }
    };

    const fetchDashboardSummary = async () => {
      try {
        const res = await api.get("/dashboard/summary");
        dashboardSummary.value = res.data;
      } catch (error) {
        console.error("获取首页摘要失败:", error);
      }
    };

    const handleUpload = async (event) => {
      const file = event.target.files[0];
      if (!file) return;

      const isCsvFile =
        file.name?.toLowerCase().endsWith(".csv") ||
        file.type === "text/csv" ||
        file.type === "application/vnd.ms-excel";

      if (!isCsvFile) {
        feedbackText.value = "请选择 CSV 文件";
        feedbackType.value = "warning";
        event.target.value = "";
        return;
      }

      if (file.size <= 0) {
        feedbackText.value = "上传文件不能为空";
        feedbackType.value = "warning";
        event.target.value = "";
        return;
      }

      if (file.size > MAX_UPLOAD_SIZE) {
        feedbackText.value = "上传文件不能超过 50 MB";
        feedbackType.value = "warning";
        event.target.value = "";
        return;
      }

      const formData = new FormData();
      formData.append("file", file);
      feedbackText.value = "";

      try {
        const res = await api.post("/upload", formData, {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        });

        feedbackText.value = "文件上传成功";
        feedbackType.value = "success";

        await fetchFiles(false);
        await fetchDashboardSummary();

        if (res.data?.filename) {
          await selectFile(res.data.filename);
        }
      } catch (error) {
        feedbackText.value =
          error.response?.data?.detail ||
          error.response?.data?.msg ||
          "文件上传失败";
        feedbackType.value = "error";
      } finally {
        event.target.value = "";
      }
    };

    const deleteFile = async (filename) => {
      const ok = window.confirm(
        `确认删除文件：${formatDisplayName(filename)} 吗？`
      );
      if (!ok) return;

      try {
        await api.delete(`/files/${encodeURIComponent(filename)}`);
        feedbackText.value = "文件删除成功";
        feedbackType.value = "success";

        if (selectedFile.value === filename) {
          resetSelectedFileState();
        }

        await fetchFiles();
        await fetchHistory();
        await fetchDashboardSummary();
      } catch (error) {
        feedbackText.value = error.response?.data?.detail || "文件删除失败";
        feedbackType.value = "error";
      }
    };

    const selectFile = async (filename) => {
      selectedFile.value = filename;
      clearChartInstance();
      clearDistributionChartInstance();
      clearCorrelationChartInstance();
      clearPredictionChartInstance();

      chartData.value = null;
      distributionResult.value = null;
      predictionResult.value = null;
      currentColumn.value = "";
      currentChartType.value = "";
      resetChartExportState();
      feedbackText.value = "";
      resetCleaningState();
      resetQueryState();
      resetGroupByState();
      resetDistributionState();
      resetPredictionState();
      analysisPlans.value = [];
      resetAiAssistantState();
      planForm.value.name = "";
      applyingPlanId.value = null;
      deletingPlanId.value = null;

      await Promise.all([
        loadPreview(filename),
        loadAnalysis(filename),
        loadQuality(filename),
        fetchFieldProfiles(filename),
        fetchCleaningHistory(filename),
        fetchAnalysisPlans(filename),
      ]);

      if (analysis.value?.numeric_columns?.length) {
        currentColumn.value = analysis.value.numeric_columns[0];
        predictionForm.value.targetColumn = analysis.value.numeric_columns[0];
      } else if (analysis.value?.categorical_columns?.length) {
        currentColumn.value = analysis.value.categorical_columns[0];
      }

      if (currentColumn.value) {
        currentChartType.value = getDefaultChartType(currentColumn.value);
        distributionForm.value.column = currentColumn.value;
      } else if (previewColumns.value.length) {
        distributionForm.value.column = previewColumns.value[0];
      }

      await runQueryPreview();
    };

    const selectChartColumn = async (column) => {
      currentColumn.value = column;
      const defaultType = getDefaultChartType(column);
      currentChartType.value = defaultType;
      await loadChart(column, defaultType);
    };

    const loadPreview = async (filename) => {
      loadingPreview.value = true;

      try {
        const res = await api.get(`/preview/${encodeURIComponent(filename)}`);
        previewColumns.value = res.data.columns || [];
        previewData.value = res.data.data || [];
      } catch (error) {
        feedbackText.value = "数据预览失败";
        feedbackType.value = "error";
      } finally {
        loadingPreview.value = false;
      }
    };

    const loadAnalysis = async (filename) => {
      loadingAnalysis.value = true;

      try {
        const res = await api.get(`/analyze/${encodeURIComponent(filename)}`);
        analysis.value = res.data;
        if (correlationView.value === "heatmap") {
          await nextTick();
          await renderCorrelationHeatmap();
        } else {
          clearCorrelationChartInstance();
        }
      } catch (error) {
        feedbackText.value = "数据分析失败";
        feedbackType.value = "error";
      } finally {
        loadingAnalysis.value = false;
      }
    };

    const loadQuality = async (filename) => {
      loadingQuality.value = true;

      try {
        const res = await api.get(`/quality/${encodeURIComponent(filename)}`);
        qualityReport.value = res.data;
      } catch (error) {
        feedbackText.value = "数据质量检查失败";
        feedbackType.value = "error";
      } finally {
        loadingQuality.value = false;
      }
    };

    const fetchFieldProfiles = async (filename = selectedFile.value) => {
      if (!filename) {
        fieldProfileReport.value = null;
        return;
      }

      loadingFieldProfiles.value = true;
      try {
        const res = await api.get(
          `/field-profiles/${encodeURIComponent(filename)}`
        );
        fieldProfileReport.value = res.data;
      } catch (error) {
        console.error("获取字段画像失败:", error);
        fieldProfileReport.value = null;
      } finally {
        loadingFieldProfiles.value = false;
      }
    };

    const fetchCleaningHistory = async (filename = selectedFile.value) => {
      if (!filename) {
        cleaningHistory.value = {
          current_file: null,
          lineage: [],
          descendants: [],
          can_rollback: false,
        };
        return;
      }

      loadingCleaningHistory.value = true;
      try {
        const res = await api.get(
          `/cleaning/history/${encodeURIComponent(filename)}`
        );
        cleaningHistory.value = res.data || {
          current_file: null,
          lineage: [],
          descendants: [],
          can_rollback: false,
        };
      } catch (error) {
        console.error("获取清洗历史失败:", error);
        cleaningHistory.value = {
          current_file: null,
          lineage: [],
          descendants: [],
          can_rollback: false,
        };
      } finally {
        loadingCleaningHistory.value = false;
      }
    };

    const buildQueryPreviewPayload = (offset = queryForm.value.offset) => {
      return {
        filters: queryForm.value.filters.map((item) => ({
          column: item.column,
          operator: item.operator,
          value:
            item.operator === "in"
              ? String(item.value)
                  .split(",")
                  .map((part) => part.trim())
                  .filter(Boolean)
              : item.value,
          second_value: item.secondValue || null,
        })),
        sort: queryForm.value.sortColumn
          ? [
              {
                column: queryForm.value.sortColumn,
                direction: queryForm.value.sortDirection,
              },
            ]
          : [],
        limit: Number(queryForm.value.limit) || 20,
        offset,
      };
    };

    const buildAnalysisPlanPayload = () => ({
      query: buildQueryPreviewPayload(0),
      groupby: {
        primary_group_column: groupByForm.value.primaryGroupColumn,
        secondary_group_column: groupByForm.value.secondaryGroupColumn,
        metric_column: groupByForm.value.metricColumn,
        metric_aggregation: groupByForm.value.metricAggregation,
        metrics: groupByForm.value.metrics.map((item) => ({
          column: item.column,
          aggregations: [...item.aggregations],
        })),
        limit: Number(groupByForm.value.limit) || 20,
      },
      distribution: {
        column: distributionForm.value.column,
        mode: distributionForm.value.mode,
        bins: Number(distributionForm.value.bins) || 8,
        include_cumulative: distributionForm.value.includeCumulative,
        sort_mode: distributionForm.value.sortMode,
        limit: Number(distributionForm.value.limit) || 20,
      },
      correlation: {
        view: correlationView.value,
        abs_threshold: Number(correlationAbsThreshold.value) || 0,
      },
      chart: {
        column: currentColumn.value,
        chart_type: currentChartType.value,
      },
    });

    const getDownloadFilename = (headers, fallbackName) => {
      const contentDisposition =
        headers?.["content-disposition"] || headers?.["Content-Disposition"] || "";

      const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
      if (utf8Match?.[1]) {
        return decodeURIComponent(utf8Match[1]);
      }

      const plainMatch = contentDisposition.match(/filename="?([^"]+)"?/i);
      if (plainMatch?.[1]) {
        return plainMatch[1];
      }

      return fallbackName;
    };

    const triggerBlobDownload = (blob, filename) => {
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(blobUrl);
    };

    const dataUrlToBlob = (dataUrl) => {
      const [header, base64Data] = String(dataUrl || "").split(",");
      const mimeType =
        header?.match(/data:(.*?);base64/i)?.[1] || "image/png";
      const byteString = window.atob(base64Data || "");
      const bytes = new Uint8Array(byteString.length);

      for (let index = 0; index < byteString.length; index += 1) {
        bytes[index] = byteString.charCodeAt(index);
      }

      return new Blob([bytes], { type: mimeType });
    };

    const downloadExportFile = async ({
      target,
      url,
      method = "get",
      data = null,
      fallbackName = "export.csv",
      successText = "导出成功",
    }) => {
      if (!selectedFile.value) {
        feedbackText.value = "请先选择文件";
        feedbackType.value = "warning";
        return;
      }

      exportingTarget.value = target;

      try {
        const res = await api.request({
          url,
          method,
          data,
          responseType: "blob",
        });
        const filename = getDownloadFilename(res.headers, fallbackName);
        triggerBlobDownload(res.data, filename);
        feedbackText.value = successText;
        feedbackType.value = "success";
      } catch (error) {
        feedbackText.value =
          error.response?.data?.detail || "导出失败";
        feedbackType.value = "error";
      } finally {
        exportingTarget.value = "";
      }
    };

    const openChartExportPanel = async () => {
      if (!chartData.value) {
        feedbackText.value = "\u8bf7\u5148\u751f\u6210\u56fe\u8868";
        feedbackType.value = "warning";
        return;
      }

      const generated = generatedChartPresentation.value;
      chartExportForm.value = {
        title: generated.title,
        xAxisLabel: generated.xAxisLabel,
        yAxisLabel: generated.yAxisLabel,
      };
      showChartExportPanel.value = true;

      if (activeWorkspaceSection.value === "visualization") {
        await nextTick();
        await renderChart();
      }
    };

    const cancelChartExportPanel = async () => {
      resetChartExportState();

      if (chartData.value && activeWorkspaceSection.value === "visualization") {
        await nextTick();
        await renderChart();
      }
    };

    const exportChartImage = async () => {
      if (!chartData.value) {
        feedbackText.value = "\u8bf7\u5148\u751f\u6210\u56fe\u8868";
        feedbackType.value = "warning";
        return;
      }

      exportingTarget.value = "chart";

      try {
        if (!chartInstance) {
          await nextTick();
          await renderChart();
        }

        if (!chartInstance) {
          throw new Error("chart instance unavailable");
        }

        const imageUrl = chartInstance.getDataURL({
          type: "png",
          pixelRatio: 2,
          backgroundColor: "#ffffff",
        });
        const imageBlob = dataUrlToBlob(imageUrl);
        const filename = `${sanitizeDownloadStem(
          activeChartPresentation.value.title,
          currentColumn.value || "chart"
        )}.png`;

        triggerBlobDownload(imageBlob, filename);
        feedbackText.value = "\u56fe\u8868\u5df2\u5bfc\u51fa\u4e3a PNG";
        feedbackType.value = "success";

        resetChartExportState();

        if (activeWorkspaceSection.value === "visualization") {
          await nextTick();
          await renderChart();
        }
      } catch (error) {
        feedbackText.value = "\u56fe\u8868\u5bfc\u51fa\u5931\u8d25";
        feedbackType.value = "error";
      } finally {
        exportingTarget.value = "";
      }
    };

    const fillAiQuestion = (question) => {
      aiAssistantForm.value.question = question;
      showAiAssistantDrawer.value = true;
    };

    const askAiAssistant = async (questionOverride = "", options = {}) => {
      const mode = options.mode || "question";
      const modeLabel = options.modeLabel || AI_MESSAGE_MODE_LABELS[mode] || "AI 分析";

      if (!selectedFile.value) {
        feedbackText.value = "请先选择文件";
        feedbackType.value = "warning";
        return;
      }

      if (!aiStatus.value.enabled) {
        feedbackText.value = "AI 助手尚未配置完成";
        feedbackType.value = "warning";
        return;
      }

      const question = (questionOverride || aiAssistantForm.value.question || "").trim();
      if (!question) {
        feedbackText.value = "请输入想让 AI 帮你分析的问题";
        feedbackType.value = "warning";
        return;
      }

      showAiAssistantDrawer.value = true;
      loadingAiAssistant.value = true;
      aiAssistantLastError.value = "";
      aiAssistantStage.value = "context";
      aiAssistantMessages.value.push({
        role: "user",
        content: question,
        mode,
        modeLabel,
      });

      const stageTimers = [
        setTimeout(() => {
          if (loadingAiAssistant.value) aiAssistantStage.value = "model";
        }, 600),
        setTimeout(() => {
          if (loadingAiAssistant.value) aiAssistantStage.value = "compose";
        }, 4500),
      ];

      try {
        const conversation = aiAssistantMessages.value
          .slice(-6)
          .map((item) => ({
            role: item.role,
            content: item.content,
          }));

        const res = await api.post(
          `/ai/assistant/${encodeURIComponent(selectedFile.value)}`,
          {
            question,
            conversation,
            workspace_state: {
              active_section: activeWorkspaceSection.value,
              current_column: currentColumn.value,
              current_chart_type: currentChartType.value,
            },
          }
          ,
          {
            timeout: 120000,
          }
        );

        aiAssistantStage.value = "done";
        aiAssistantMessages.value.push({
          role: "assistant",
          content: res.data?.answer || "AI 已返回一份分析建议。",
          insights: res.data?.insights || [],
          cautions: res.data?.cautions || [],
          suggestedActions: res.data?.suggested_actions || [],
          provider: res.data?.provider || aiStatus.value.provider,
          model: res.data?.model || aiStatus.value.model,
          mode,
          modeLabel,
        });
        aiAssistantForm.value.question = "";
        aiAssistantLastCompletedAt.value = new Date().toISOString();
        feedbackText.value = "";
      } catch (error) {
        const message = getAiErrorMessage(error);
        aiAssistantStage.value = "error";
        aiAssistantLastError.value = message;
        aiAssistantMessages.value.push({
          role: "assistant",
          content: message,
          insights: [],
          cautions: [],
          suggestedActions: [],
          provider: aiStatus.value.provider,
          model: aiStatus.value.model,
          isError: true,
          mode,
          modeLabel,
        });
        feedbackText.value = message;
        feedbackType.value = "error";
      } finally {
        stageTimers.forEach((timer) => clearTimeout(timer));
        loadingAiAssistant.value = false;
        if (aiAssistantStage.value === "done") {
          setTimeout(() => {
            if (!loadingAiAssistant.value && aiAssistantStage.value === "done") {
              aiAssistantStage.value = "idle";
            }
          }, 1200);
        }
      }
    };

    const clearAiConversation = () => {
      resetAiAssistantState();
      showAiAssistantDrawer.value = true;
    };

    const explainCurrentAnalysisResult = async () => {
      const prompt = buildAiCurrentResultPrompt();
      if (!prompt) {
        feedbackText.value = "当前模块还没有足够的分析结果可供 AI 解读";
        feedbackType.value = "warning";
        return;
      }
      showAiAssistantDrawer.value = true;
      await askAiAssistant(prompt, {
        mode: "explain",
        modeLabel: AI_MESSAGE_MODE_LABELS.explain,
      });
    };

    const generateAiPresentationSummary = async () => {
      const prompt = buildAiPresentationSummaryPrompt();
      if (!prompt) {
        feedbackText.value = "请先完成至少一项分析，再让 AI 生成展示摘要";
        feedbackType.value = "warning";
        return;
      }
      showAiAssistantDrawer.value = true;
      await askAiAssistant(prompt, {
        mode: "presentation",
        modeLabel: AI_MESSAGE_MODE_LABELS.presentation,
      });
    };

    const applyAiSuggestedAction = async (action) => {
      if (!action?.action_type) return;

      const params = action.params || {};

      if (action.target_section) {
        setWorkspaceSection(action.target_section);
      }

      if (action.action_type === "chart" && params.column) {
        await nextTick();
        await loadChart(
          params.column,
          params.chart_type || getDefaultChartType(params.column)
        );
        return;
      }

      if (action.action_type === "distribution" && params.column) {
        distributionForm.value = {
          ...distributionForm.value,
          column: params.column,
          mode: params.mode || "auto",
        };
        await nextTick();
        await runDistributionAnalysis();
        return;
      }

      if (action.action_type === "groupby" && params.primary_group_column) {
        const nextAggregation = params.metric_aggregation || "count";
        groupByForm.value = {
          ...groupByForm.value,
          primaryGroupColumn: params.primary_group_column,
          secondaryGroupColumn: params.secondary_group_column || "",
          metricColumn: params.metric_column || "",
          metricAggregation: nextAggregation,
          metrics: params.metric_column
            ? [
                {
                  column: params.metric_column,
                  aggregations: [nextAggregation],
                },
              ]
            : [],
        };
        await nextTick();
        await runGroupBy();
        return;
      }

      if (action.action_type === "correlation") {
        await nextTick();
        await setCorrelationView("heatmap");
      }
    };

    const runQueryPreview = async (offset = queryForm.value.offset) => {
      if (!selectedFile.value) {
        return;
      }

      loadingQueryPreview.value = true;

      try {
        const nextOffset = Math.max(0, Number(offset) || 0);
        const payload = buildQueryPreviewPayload(nextOffset);
        const res = await api.post(
          `/query/preview/${encodeURIComponent(selectedFile.value)}`,
          payload
        );
        queryPreviewResult.value = res.data;
        queryForm.value.offset = res.data.offset || nextOffset;
        feedbackText.value = "";
      } catch (error) {
        feedbackText.value =
          error.response?.data?.detail || "查询预览加载失败";
        feedbackType.value = "error";
        queryPreviewResult.value = null;
      } finally {
        loadingQueryPreview.value = false;
      }
    };

    const clearQueryPreview = async () => {
      resetQueryState();
      if (selectedFile.value) {
        await runQueryPreview(0);
      }
    };

    const changeQueryPage = async (direction) => {
      if (!queryPreviewResult.value) return;
      const step = queryPreviewResult.value.limit || Number(queryForm.value.limit) || 20;
      const nextOffset =
        direction === "next"
          ? (queryPreviewResult.value.offset || 0) + step
          : Math.max((queryPreviewResult.value.offset || 0) - step, 0);
      await runQueryPreview(nextOffset);
    };

    const renderDistributionChart = async () => {
      clearDistributionChartInstance();
      if (!distributionChartRef.value || !distributionResult.value?.chart) return;
      const echarts = await getEcharts();
      distributionChartInstance = echarts.init(distributionChartRef.value);

      const chart = distributionResult.value.chart;
      const includeCumulative =
        distributionResult.value.include_cumulative &&
        chart.cumulative_percentages?.length;

      distributionChartInstance.setOption({
        backgroundColor: "transparent",
        tooltip: {
          trigger: "axis",
        },
        legend: {
          bottom: 0,
          data: includeCumulative ? ["频数", "累计频率"] : ["频数"],
        },
        grid: {
          left: 48,
          right: includeCumulative ? 64 : 28,
          top: 36,
          bottom: 52,
        },
        xAxis: {
          type: "category",
          data: chart.categories || [],
          axisLine: { lineStyle: { color: "#cbd5e1" } },
          axisLabel: { color: "#64748b", interval: 0, rotate: 22 },
        },
        yAxis: includeCumulative
          ? [
              {
                type: "value",
                name: "频数",
                axisLine: { show: false },
                splitLine: { lineStyle: { color: "#e8eef7" } },
                axisLabel: { color: "#64748b" },
              },
              {
                type: "value",
                name: "累计频率",
                min: 0,
                max: 100,
                axisLine: { show: false },
                splitLine: { show: false },
                axisLabel: {
                  color: "#64748b",
                  formatter: "{value}%",
                },
              },
            ]
          : {
              type: "value",
              name: "频数",
              axisLine: { show: false },
              splitLine: { lineStyle: { color: "#e8eef7" } },
              axisLabel: { color: "#64748b" },
            },
        series: [
          {
            name: "频数",
            type: "bar",
            data: chart.counts || [],
            barMaxWidth: 34,
            itemStyle: {
              borderRadius: 10,
              color: {
                type: "linear",
                x: 0,
                y: 0,
                x2: 1,
                y2: 1,
                colorStops: [
                  { offset: 0, color: "#5b8cff" },
                  { offset: 1, color: "#ff9f43" },
                ],
              },
            },
          },
          ...(includeCumulative
            ? [
                {
                  name: "累计频率",
                  type: "line",
                  yAxisIndex: 1,
                  smooth: true,
                  symbolSize: 8,
                  data: chart.cumulative_percentages || [],
                  lineStyle: { width: 3, color: "#ff7a59" },
                  itemStyle: { color: "#ff7a59" },
                },
              ]
            : []),
        ],
      });
    };

    const renderCorrelationHeatmap = async () => {
      clearCorrelationChartInstance();
      if (!correlationChartRef.value || !correlationColumns.value.length) return;

      const echarts = await getEcharts();
      correlationChartInstance = echarts.init(correlationChartRef.value);
      const showAllLabels = correlationColumns.value.length <= 12;

      correlationChartInstance.setOption({
        backgroundColor: "transparent",
        tooltip: {
          position: "top",
          formatter: (params) => {
            const [columnIndex, rowIndex, rawValue] = params.data || [];
            const xLabel = correlationColumns.value[columnIndex] || "";
            const yLabel = correlationColumns.value[rowIndex] || "";
            const valueLabel =
              rawValue === null || rawValue === undefined
                ? "无有效值"
                : Number(rawValue).toFixed(4);
            const strengthLabel =
              rawValue === null || rawValue === undefined
                ? "低于当前阈值或无有效值"
                : getCorrelationStrengthLabel(rawValue);

            return `${yLabel} × ${xLabel}<br/>相关系数：${valueLabel}<br/>关系强度：${strengthLabel}`;
          },
        },
        grid: {
          left: 96,
          right: 28,
          top: 36,
          bottom: 80,
        },
        xAxis: {
          type: "category",
          data: correlationColumns.value,
          axisLine: { lineStyle: { color: "#cbd5e1" } },
          axisLabel: {
            color: "#64748b",
            interval: showAllLabels ? 0 : "auto",
            rotate: correlationColumns.value.length > 6 ? 28 : 0,
            formatter: (value) =>
              value.length > 12 ? `${value.slice(0, 12)}...` : value,
          },
        },
        yAxis: {
          type: "category",
          data: correlationColumns.value,
          axisLine: { lineStyle: { color: "#cbd5e1" } },
          axisLabel: {
            color: "#64748b",
            interval: showAllLabels ? 0 : "auto",
            formatter: (value) =>
              value.length > 12 ? `${value.slice(0, 12)}...` : value,
          },
        },
        visualMap: {
          min: -1,
          max: 1,
          calculable: false,
          orient: "horizontal",
          left: "center",
          bottom: 12,
          text: ["正相关", "负相关"],
          textStyle: { color: "#64748b" },
          inRange: {
            color: ["#4f67ff", "#f8fbff", "#ffb14a"],
          },
        },
        series: [
          {
            type: "heatmap",
            data: correlationHeatmapData.value,
            itemStyle: {
              borderColor: "#e2e8f0",
              borderWidth: 1,
            },
            label: {
              show: correlationColumns.value.length <= 8,
              formatter: ({ data }) => {
                const value = data?.[2];
                return value === null || value === undefined
                  ? "-"
                  : Number(value).toFixed(2);
              },
              color: "#0f172a",
              fontWeight: 600,
            },
            emphasis: {
              itemStyle: {
                shadowBlur: 14,
                shadowColor: "rgba(79, 140, 255, 0.24)",
              },
            },
          },
        ],
      });
    };

    const collectGroupByRequestState = (syncFormState = false) => {
      const groupColumns = [
        groupByForm.value.primaryGroupColumn,
        groupByForm.value.secondaryGroupColumn,
      ].filter(Boolean);

      let metrics = [...groupByForm.value.metrics];

      if (groupByForm.value.metricColumn) {
        const mergedMetricResult = mergeGroupMetric(
          metrics,
          groupByForm.value.metricColumn,
          groupByForm.value.metricAggregation
        );
        metrics = mergedMetricResult.metrics;

        if (syncFormState) {
          groupByForm.value.metrics = metrics;
          groupByForm.value.metricColumn = "";
          groupByForm.value.metricAggregation = "count";
        }
      }

      return { groupColumns, metrics };
    };

    const buildDistributionRequestPayload = () => ({
      filters: buildQueryPreviewPayload(0).filters,
      column: distributionForm.value.column,
      mode: distributionForm.value.mode,
      bins: Number(distributionForm.value.bins) || 8,
      include_cumulative: distributionForm.value.includeCumulative,
      sort_mode: distributionForm.value.sortMode,
      limit: Number(distributionForm.value.limit) || 20,
    });

    const exportQueryResult = async () => {
      await downloadExportFile({
        target: "query",
        url: `/export/query/${encodeURIComponent(selectedFile.value)}`,
        method: "post",
        data: buildQueryPreviewPayload(0),
        fallbackName: "query_result.csv",
        successText: "查询结果已开始导出",
      });
    };

    const exportGroupByResult = async () => {
      const { groupColumns, metrics } = collectGroupByRequestState(false);

      if (!groupColumns.length) {
        feedbackText.value = "请先选择至少一个分组字段";
        feedbackType.value = "warning";
        return;
      }

      if (
        groupByForm.value.primaryGroupColumn &&
        groupByForm.value.primaryGroupColumn === groupByForm.value.secondaryGroupColumn
      ) {
        feedbackText.value = "主分组字段和次分组字段不能相同";
        feedbackType.value = "warning";
        return;
      }

      await downloadExportFile({
        target: "groupby",
        url: `/export/groupby/${encodeURIComponent(selectedFile.value)}`,
        method: "post",
        data: {
          filters: buildQueryPreviewPayload(0).filters,
          group_columns: groupColumns,
          metrics: metrics.map((item) => ({
            column: item.column,
            aggregations: item.aggregations,
          })),
          limit: Number(groupByForm.value.limit) || 20,
        },
        fallbackName: "group_statistics.csv",
        successText: "分组结果已开始导出",
      });
    };

    const exportDistributionResult = async () => {
      if (!distributionForm.value.column) {
        feedbackText.value = "请先选择需要分析分布的字段";
        feedbackType.value = "warning";
        return;
      }

      await downloadExportFile({
        target: "distribution",
        url: `/export/distribution/${encodeURIComponent(selectedFile.value)}`,
        method: "post",
        data: buildDistributionRequestPayload(),
        fallbackName: "distribution.csv",
        successText: "频数分布结果已开始导出",
      });
    };

    const exportStatisticsResult = async () => {
      await downloadExportFile({
        target: "statistics",
        url: `/export/statistics/${encodeURIComponent(selectedFile.value)}`,
        method: "get",
        fallbackName: "statistics.csv",
        successText: "描述统计结果已开始导出",
      });
    };

    const exportCorrelationResult = async () => {
      await downloadExportFile({
        target: "correlation",
        url: `/export/correlation/${encodeURIComponent(selectedFile.value)}`,
        method: "get",
        fallbackName: "correlation_matrix.csv",
        successText: "相关矩阵已开始导出",
      });
    };

    const saveAnalysisPlan = async () => {
      if (!selectedFile.value) {
        feedbackText.value = "请先选择文件";
        feedbackType.value = "warning";
        return;
      }

      const planName = planForm.value.name.trim();
      if (!planName) {
        feedbackText.value = "请先输入方案名称";
        feedbackType.value = "warning";
        return;
      }

      savingPlan.value = true;
      try {
        const res = await api.post(
          `/plans/${encodeURIComponent(selectedFile.value)}`,
          {
            name: planName,
            plan: buildAnalysisPlanPayload(),
          }
        );
        feedbackText.value = res.data?.msg || "分析方案已保存";
        feedbackType.value = "success";
        planForm.value.name = "";
        await fetchAnalysisPlans(selectedFile.value);
      } catch (error) {
        feedbackText.value =
          error.response?.data?.detail || "分析方案保存失败";
        feedbackType.value = "error";
      } finally {
        savingPlan.value = false;
      }
    };

    const applyAnalysisPlan = async (plan) => {
      if (!plan?.config) return;

      if (plan.stored_name && plan.stored_name !== selectedFile.value) {
        await selectFile(plan.stored_name);
      }

      applyingPlanId.value = plan.id;
      try {
        const validColumns = new Set(availableQueryColumns.value);
        const queryConfig = plan.config.query || {};
        const groupbyConfig = plan.config.groupby || {};
        const distributionConfig = plan.config.distribution || {};
        const correlationConfig = plan.config.correlation || {};
        const chartConfig = plan.config.chart || {};
        const sortRule = Array.isArray(queryConfig.sort) ? queryConfig.sort[0] : null;
        const nextSortColumn = validColumns.has(sortRule?.column)
          ? sortRule.column
          : "";

        queryForm.value = {
          filterColumn: "",
          filterOperator: "eq",
          filterValue: "",
          filterSecondValue: "",
          filters: (queryConfig.filters || [])
            .filter((item) => validColumns.has(item.column))
            .map((item) => ({
              column: item.column,
              operator: item.operator || "eq",
              value: Array.isArray(item.value) ? item.value.join(", ") : item.value ?? "",
              secondValue: item.second_value ?? "",
            })),
          sortColumn: nextSortColumn,
          sortDirection:
            nextSortColumn && sortRule?.direction === "desc" ? "desc" : "asc",
          limit: Number(queryConfig.limit) || 20,
          offset: 0,
        };

        const sanitizedMetrics = (groupbyConfig.metrics || [])
          .filter((item) => validColumns.has(item.column))
          .map((item) => ({
            column: item.column,
            aggregations: normalizeGroupAggregations(item.aggregations),
          }));

        const primaryGroupColumn = validColumns.has(groupbyConfig.primary_group_column)
          ? groupbyConfig.primary_group_column
          : "";
        const secondaryGroupColumn =
          validColumns.has(groupbyConfig.secondary_group_column) &&
          groupbyConfig.secondary_group_column !== primaryGroupColumn
            ? groupbyConfig.secondary_group_column
            : "";

        groupByForm.value = {
          primaryGroupColumn,
          secondaryGroupColumn,
          metricColumn: validColumns.has(groupbyConfig.metric_column)
            ? groupbyConfig.metric_column
            : "",
          metricAggregation: normalizeGroupAggregations([
            groupbyConfig.metric_aggregation || "count",
          ])[0],
          metrics: sanitizedMetrics,
          limit: Number(groupbyConfig.limit) || 20,
        };

        distributionForm.value = {
          column: validColumns.has(distributionConfig.column)
            ? distributionConfig.column
            : "",
          mode: DISTRIBUTION_MODE_OPTIONS.some(
            (option) => option.value === distributionConfig.mode
          )
            ? distributionConfig.mode
            : "auto",
          bins: Number(distributionConfig.bins) || 8,
          includeCumulative:
            distributionConfig.include_cumulative !== undefined
              ? Boolean(distributionConfig.include_cumulative)
              : true,
          sortMode: DISTRIBUTION_SORT_OPTIONS.some(
            (option) => option.value === distributionConfig.sort_mode
          )
            ? distributionConfig.sort_mode
            : "default",
          limit: Number(distributionConfig.limit) || 20,
        };

        correlationAbsThreshold.value = Number.isFinite(
          Number(correlationConfig.abs_threshold)
        )
          ? Number(correlationConfig.abs_threshold)
          : 0;
        correlationView.value = CORRELATION_VIEW_OPTIONS.some(
          (option) => option.value === correlationConfig.view
        )
          ? correlationConfig.view
          : "heatmap";

        await runQueryPreview(0);

        if (
          groupByForm.value.primaryGroupColumn ||
          groupByForm.value.secondaryGroupColumn
        ) {
          await runGroupBy();
        } else {
          groupByResult.value = null;
        }

        if (distributionForm.value.column) {
          await runDistributionAnalysis();
        } else {
          distributionResult.value = null;
          clearDistributionChartInstance();
        }

        if (correlationView.value === "heatmap") {
          await nextTick();
          await renderCorrelationHeatmap();
        } else {
          clearCorrelationChartInstance();
        }

        const availableChartColumn = validColumns.has(chartConfig.column)
          ? chartConfig.column
          : "";
        if (availableChartColumn) {
          currentColumn.value = availableChartColumn;
          const chartKind = getColumnKind(availableChartColumn);
          const supportedChartTypes =
            chartKind === "categorical"
              ? CATEGORICAL_CHART_OPTIONS.map((item) => item.value)
              : NUMERIC_CHART_OPTIONS.map((item) => item.value);
          const nextChartType = supportedChartTypes.includes(chartConfig.chart_type)
            ? chartConfig.chart_type
            : getDefaultChartType(availableChartColumn);
          await loadChart(availableChartColumn, nextChartType);
        } else {
          currentColumn.value = "";
          currentChartType.value = "";
          chartData.value = null;
          clearChartInstance();
        }

        feedbackText.value = `已恢复分析方案：${plan.name}`;
        feedbackType.value = "success";
      } catch (error) {
        feedbackText.value =
          error.response?.data?.detail || "分析方案恢复失败";
        feedbackType.value = "error";
      } finally {
        applyingPlanId.value = null;
      }
    };

    const deleteAnalysisPlan = async (planId) => {
      deletingPlanId.value = planId;
      try {
        const res = await api.delete(`/plans/${planId}`);
        feedbackText.value = res.data?.msg || "分析方案已删除";
        feedbackType.value = "success";
        await fetchAnalysisPlans(selectedFile.value);
      } catch (error) {
        feedbackText.value =
          error.response?.data?.detail || "分析方案删除失败";
        feedbackType.value = "error";
      } finally {
        deletingPlanId.value = null;
      }
    };

    const runDistributionAnalysis = async () => {
      if (!selectedFile.value) {
        feedbackText.value = "请先选择文件";
        feedbackType.value = "warning";
        return;
      }

      if (!distributionForm.value.column) {
        feedbackText.value = "请先选择需要分析分布的字段";
        feedbackType.value = "warning";
        return;
      }

      loadingDistribution.value = true;

      try {
        const payload = buildDistributionRequestPayload();

        const res = await api.post(
          `/distribution/analyze/${encodeURIComponent(selectedFile.value)}`,
          payload
        );

        distributionResult.value = res.data;
        feedbackText.value = "";
        loadingDistribution.value = false;

        await nextTick();
        await renderDistributionChart();
      } catch (error) {
        feedbackText.value =
          error.response?.data?.detail || "频数分布分析失败";
        feedbackType.value = "error";
        distributionResult.value = null;
        clearDistributionChartInstance();
        loadingDistribution.value = false;
      } finally {
        if (loadingDistribution.value) {
          loadingDistribution.value = false;
        }
      }
    };

    const runGroupBy = async () => {
      if (!selectedFile.value) {
        feedbackText.value = "请先选择文件";
        feedbackType.value = "warning";
        return;
      }

      const { groupColumns, metrics } = collectGroupByRequestState(true);

      if (!groupColumns.length) {
        feedbackText.value = "请先选择至少一个分组字段";
        feedbackType.value = "warning";
        return;
      }

      if (
        groupByForm.value.primaryGroupColumn &&
        groupByForm.value.primaryGroupColumn === groupByForm.value.secondaryGroupColumn
      ) {
        feedbackText.value = "主分组字段和次分组字段不能相同";
        feedbackType.value = "warning";
        return;
      }

      loadingGroupBy.value = true;

      try {
        const payload = {
          filters: buildQueryPreviewPayload(0).filters,
          group_columns: groupColumns,
          metrics: metrics.map((item) => ({
            column: item.column,
            aggregations: item.aggregations,
          })),
          limit: Number(groupByForm.value.limit) || 20,
        };

        const res = await api.post(
          `/groupby/analyze/${encodeURIComponent(selectedFile.value)}`,
          payload
        );
        groupByResult.value = res.data;
        feedbackText.value = "";
      } catch (error) {
        feedbackText.value =
          error.response?.data?.detail || "分组统计分析失败";
        feedbackType.value = "error";
        groupByResult.value = null;
      } finally {
        loadingGroupBy.value = false;
      }
    };

    const loadOutlierDetail = async (columnName) => {
      if (!selectedFile.value) return;

      loadingOutlierColumn.value = columnName;
      try {
        const res = await api.get(
          `/quality/${encodeURIComponent(selectedFile.value)}/outliers?column=${encodeURIComponent(
            columnName
          )}`
        );
        outlierDetailMap.value = {
          ...outlierDetailMap.value,
          [columnName]: res.data,
        };
      } catch (error) {
        feedbackText.value =
          error.response?.data?.detail || "异常值明细加载失败";
        feedbackType.value = "error";
      } finally {
        if (loadingOutlierColumn.value === columnName) {
          loadingOutlierColumn.value = "";
        }
      }
    };

    const toggleOutlierDetail = async (column) => {
      if (!column?.outlier_count) return;

      if (expandedOutlierColumn.value === column.name) {
        expandedOutlierColumn.value = "";
        return;
      }

      expandedOutlierColumn.value = column.name;
      if (!outlierDetailMap.value[column.name]) {
        await loadOutlierDetail(column.name);
      }
    };

    const previewCleaning = async () => {
      if (!selectedFile.value) {
        feedbackText.value = "请先选择文件";
        feedbackType.value = "warning";
        return;
      }

      loadingCleaningPreview.value = true;

      try {
        const res = await api.post(
          `/clean/preview/${encodeURIComponent(selectedFile.value)}`,
          {
            missing_strategy: cleaningForm.value.missingStrategy,
            fill_value: cleaningForm.value.fillValue,
            remove_duplicates: cleaningForm.value.removeDuplicates,
            outlier_strategy: cleaningForm.value.outlierStrategy,
            type_conversions: cleaningForm.value.typeConversions.map((item) => ({
              column: item.column,
              target_type: item.targetType,
            })),
          }
        );

        cleaningPreview.value = res.data;
        feedbackText.value = "已生成清洗预览";
        feedbackType.value = "success";
      } catch (error) {
        cleaningPreview.value = null;
        feedbackText.value =
          error.response?.data?.detail || "清洗预览生成失败";
        feedbackType.value = "error";
      } finally {
        loadingCleaningPreview.value = false;
      }
    };

    const applyCleaning = async () => {
      if (!selectedFile.value) {
        feedbackText.value = "请先选择文件";
        feedbackType.value = "warning";
        return;
      }

      applyingCleaning.value = true;

      try {
        const res = await api.post(
          `/clean/apply/${encodeURIComponent(selectedFile.value)}`,
          {
            missing_strategy: cleaningForm.value.missingStrategy,
            fill_value: cleaningForm.value.fillValue,
            remove_duplicates: cleaningForm.value.removeDuplicates,
            outlier_strategy: cleaningForm.value.outlierStrategy,
            type_conversions: cleaningForm.value.typeConversions.map((item) => ({
              column: item.column,
              target_type: item.targetType,
            })),
          }
        );

        feedbackText.value = res.data?.msg || "清洗完成";
        feedbackType.value = "success";
        cleaningPreview.value = null;

        await fetchFiles(false);
        await fetchDashboardSummary();

        if (res.data?.filename) {
          await selectFile(res.data.filename);
        }
      } catch (error) {
        feedbackText.value =
          error.response?.data?.detail || "清洗保存失败";
        feedbackType.value = "error";
      } finally {
        applyingCleaning.value = false;
      }
    };

    const formatCleaningOperationLabels = (historyItem) => {
      if (!historyItem?.operation_labels?.length) return "未记录处理步骤";
      return historyItem.operation_labels.join(" / ");
    };

    const jumpToCleaningHistoryFile = async (storedName) => {
      if (!storedName) return;
      await selectFile(storedName);
    };

    const rollbackCleaningHistory = async (historyItem) => {
      if (!selectedFile.value || !historyItem?.id) {
        feedbackText.value = "当前没有可回滚的清洗历史";
        feedbackType.value = "warning";
        return;
      }

      rollingBackHistoryId.value = historyItem.id;
      try {
        const res = await api.post(
          `/cleaning/rollback/${encodeURIComponent(selectedFile.value)}`,
          {
            history_id: historyItem.id,
          }
        );

        feedbackText.value = res.data?.msg || "已生成回滚文件";
        feedbackType.value = "success";
        await fetchFiles(false);
        await fetchDashboardSummary();
        if (res.data?.filename) {
          await selectFile(res.data.filename);
        } else {
          await fetchCleaningHistory(selectedFile.value);
        }
      } catch (error) {
        feedbackText.value =
          error.response?.data?.detail || "回滚文件生成失败";
        feedbackType.value = "error";
      } finally {
        rollingBackHistoryId.value = null;
      }
    };

    const renderChart = async () => {
      if (!chartRef.value || !chartData.value) return;

      clearChartInstance();
      const echarts = await getEcharts();
      chartInstance = echarts.init(chartRef.value);
      const chartPresentation = activeChartPresentation.value;
      const titleOption = chartPresentation.title
        ? {
            text: chartPresentation.title,
            left: "center",
            top: 10,
            textStyle: {
              color: "#0f172a",
              fontSize: 16,
              fontWeight: 700,
            },
          }
        : undefined;

      let option = {};

      if (chartData.value.type === "pie") {
        option = {
          backgroundColor: "transparent",
          title: titleOption,
          tooltip: { trigger: "item" },
          legend: { bottom: 0 },
          series: [
            {
              type: "pie",
              radius: chartData.value.radius || "62%",
              roseType: chartData.value.rose_type,
              center: ["50%", "54%"],
              data: chartData.value.data || [],
              label: {
                formatter: "{b}: {d}%",
              },
            },
          ],
        };
      } else if (chartData.value.type === "treemap") {
        option = {
          backgroundColor: "transparent",
          title: titleOption,
          tooltip: { trigger: "item" },
          series: [
            {
              type: "treemap",
              top: 60,
              left: 8,
              right: 8,
              bottom: 8,
              roam: false,
              breadcrumb: { show: false },
              nodeClick: false,
              label: {
                formatter: "{b}\n{c}",
              },
              data: chartData.value.data || [],
            },
          ],
        };
      } else if (chartData.value.type === "boxplot") {
        option = {
          backgroundColor: "transparent",
          title: titleOption,
          tooltip: { trigger: "item" },
          grid: {
            left: 72,
            right: 28,
            top: 82,
            bottom: 72,
          },
          xAxis: {
            type: "category",
            data: chartData.value.x || [],
            name: chartPresentation.xAxisLabel,
            nameLocation: "middle",
            nameGap: 42,
            nameTextStyle: {
              color: "#475569",
              fontWeight: 600,
            },
            axisLine: { lineStyle: { color: "#cbd5e1" } },
            axisLabel: { color: "#64748b" },
          },
          yAxis: {
            type: "value",
            name: chartPresentation.yAxisLabel,
            nameLocation: "middle",
            nameGap: 56,
            nameTextStyle: {
              color: "#475569",
              fontWeight: 600,
            },
            axisLine: { show: false },
            splitLine: { lineStyle: { color: "#e8eef7" } },
            axisLabel: { color: "#64748b" },
          },
          series: [
            {
              type: "boxplot",
              data: chartData.value.data || [],
              itemStyle: {
                color: "rgba(91, 140, 255, 0.35)",
                borderColor: "#5b8cff",
              },
            },
          ],
        };
      } else {
        const isHorizontal = chartData.value.orientation === "horizontal";
        const categories = chartData.value.categories || chartData.value.x || [];
        const values = chartData.value.values || chartData.value.y || [];
        const seriesType =
          chartData.value.type === "area"
            ? "line"
            : chartData.value.type || "bar";

        option = {
          backgroundColor: "transparent",
          title: titleOption,
          tooltip: {
            trigger: seriesType === "bar" ? "item" : "axis",
          },
          grid: {
            left: 76,
            right: 28,
            top: 82,
            bottom: 72,
          },
          xAxis: isHorizontal
            ? {
                type: "value",
                name: chartPresentation.xAxisLabel,
                nameLocation: "middle",
                nameGap: 40,
                nameTextStyle: {
                  color: "#475569",
                  fontWeight: 600,
                },
                axisLine: { show: false },
                splitLine: { lineStyle: { color: "#e8eef7" } },
                axisLabel: { color: "#64748b" },
              }
            : {
                type: "category",
                data: categories,
                name: chartPresentation.xAxisLabel,
                nameLocation: "middle",
                nameGap: 42,
                nameTextStyle: {
                  color: "#475569",
                  fontWeight: 600,
                },
                axisLine: { lineStyle: { color: "#cbd5e1" } },
                axisLabel: { color: "#64748b" },
              },
          yAxis: isHorizontal
            ? {
                type: "category",
                data: categories,
                name: chartPresentation.yAxisLabel,
                nameLocation: "middle",
                nameGap: 62,
                nameTextStyle: {
                  color: "#475569",
                  fontWeight: 600,
                },
                axisLine: { lineStyle: { color: "#cbd5e1" } },
                axisLabel: { color: "#64748b" },
              }
            : {
                type: "value",
                name: chartPresentation.yAxisLabel,
                nameLocation: "middle",
                nameGap: 58,
                nameTextStyle: {
                  color: "#475569",
                  fontWeight: 600,
                },
                axisLine: { show: false },
                splitLine: { lineStyle: { color: "#e8eef7" } },
                axisLabel: { color: "#64748b" },
              },
          series: [
            {
              data: values,
              type: seriesType,
              smooth: seriesType === "line",
              symbolSize: 8,
              barMaxWidth: 36,
              itemStyle: {
                borderRadius: 10,
                color: {
                  type: "linear",
                  x: 0,
                  y: 0,
                  x2: 1,
                  y2: 1,
                  colorStops: [
                    { offset: 0, color: "#5b8cff" },
                    { offset: 1, color: "#7c4dff" },
                  ],
                },
              },
              areaStyle:
                chartData.value.type === "area"
                  ? { color: "rgba(91, 140, 255, 0.12)" }
                  : undefined,
              lineStyle:
                seriesType === "line"
                  ? { width: 3, color: "#5b8cff" }
                  : undefined,
            },
          ],
        };
      }

      chartInstance.setOption(option);
    };

    const renderPredictionChart = async () => {
      if (!predictionChartRef.value || !predictionResult.value) return;

      clearPredictionChartInstance();
      await waitForAnimationFrame();
      const echarts = await getEcharts();
      predictionChartInstance = echarts.init(predictionChartRef.value);

      const historical = predictionResult.value.historical || [];
      const forecast = predictionResult.value.forecast || [];
      const labels = [
        ...historical.map((item) => item.label),
        ...forecast.map((item) => item.label),
      ];
      const historicalValues = [
        ...historical.map((item) => item.value),
        ...forecast.map(() => null),
      ];
      const forecastValues = [
        ...historical.slice(0, -1).map(() => null),
        historical.length ? historical[historical.length - 1].value : null,
        ...forecast.map((item) => item.value),
      ];

      predictionChartInstance.setOption({
        backgroundColor: "transparent",
        tooltip: {
          trigger: "axis",
          valueFormatter: (value) => formatCompactNumber(value),
        },
        legend: {
          top: 8,
          right: 12,
          data: ["历史数据", "预测数据"],
        },
        grid: {
          left: 76,
          right: 30,
          top: 58,
          bottom: 68,
        },
        xAxis: {
          type: "category",
          data: labels,
          name: predictionResult.value.feature_label || "序列",
          nameLocation: "middle",
          nameGap: 42,
          axisLine: { lineStyle: { color: "#cbd5e1" } },
          axisLabel: {
            color: "#64748b",
            hideOverlap: true,
          },
        },
        yAxis: {
          type: "value",
          name: predictionResult.value.target_column || "预测值",
          nameLocation: "middle",
          nameGap: 58,
          axisLine: { show: false },
          splitLine: { lineStyle: { color: "#e8eef7" } },
          axisLabel: { color: "#64748b" },
        },
        series: [
          {
            name: "历史数据",
            type: "line",
            smooth: true,
            symbolSize: 7,
            data: historicalValues,
            lineStyle: { width: 3, color: "#5b8cff" },
            itemStyle: { color: "#5b8cff" },
            areaStyle: { color: "rgba(91, 140, 255, 0.1)" },
          },
          {
            name: "预测数据",
            type: "line",
            smooth: true,
            symbolSize: 8,
            data: forecastValues,
            lineStyle: {
              width: 3,
              color: "#f59e0b",
              type: "dashed",
            },
            itemStyle: { color: "#f59e0b" },
            areaStyle: { color: "rgba(245, 158, 11, 0.12)" },
          },
        ],
      });
      predictionChartInstance.resize();
    };

    const runPrediction = async () => {
      if (!selectedFile.value) {
        feedbackText.value = "请先选择文件";
        feedbackType.value = "warning";
        return;
      }

      if (!predictionForm.value.targetColumn) {
        feedbackText.value = "请选择要预测的数值字段";
        feedbackType.value = "warning";
        return;
      }

      const periods = Number(predictionForm.value.periods) || 6;
      loadingPrediction.value = true;

      try {
        const res = await api.post(
          `/predict/${encodeURIComponent(selectedFile.value)}`,
          {
            target_column: predictionForm.value.targetColumn,
            feature_column: predictionForm.value.featureColumn || null,
            periods: Math.min(Math.max(periods, 1), 60),
          }
        );

        predictionResult.value = res.data;
        feedbackText.value = "已生成未来数据预测";
        feedbackType.value = "success";
        loadingPrediction.value = false;

        await nextTick();
        await waitForAnimationFrame();
        await renderPredictionChart();
      } catch (error) {
        predictionResult.value = null;
        clearPredictionChartInstance();
        feedbackText.value =
          error.response?.data?.detail || "数据预测失败";
        feedbackType.value = "error";
      } finally {
        loadingPrediction.value = false;
      }
    };

    const loadChart = async (
      column,
      chartType = currentChartType.value || getDefaultChartType(column)
    ) => {
      if (!selectedFile.value) {
        feedbackText.value = "请先选择文件";
        feedbackType.value = "warning";
        return;
      }

      resetChartExportState();
      loadingChart.value = true;
      currentChartType.value = chartType;

      try {
        const res = await api.get(
          `/chart/${encodeURIComponent(selectedFile.value)}?column=${encodeURIComponent(
            column
          )}&chart_type=${encodeURIComponent(chartType)}`
        );

        chartData.value = res.data;
        currentColumn.value = column;
        currentChartType.value = res.data.resolved_type || chartType;
        feedbackText.value = "";

        await fetchHistory();
        await fetchDashboardSummary();

        loadingChart.value = false;
        await nextTick();
        await renderChart();
      } catch (error) {
        feedbackText.value =
          error.response?.data?.detail || "图表加载失败";
        feedbackType.value = "error";
        chartData.value = null;
        loadingChart.value = false;
      }
    };

    const statRows = computed(() => {
      if (!analysis.value?.statistics) return [];
      const stats = analysis.value.statistics;

      return Object.keys(stats).map((name) => ({
        name,
        count: stats[name].count ?? "-",
        mean: formatNumber(stats[name].mean),
        std: formatNumber(stats[name].std),
        min: formatNumber(stats[name].min),
        q1: formatNumber(stats[name]["25%"]),
        median: formatNumber(stats[name]["50%"]),
        q3: formatNumber(stats[name]["75%"]),
        max: formatNumber(stats[name].max),
      }));
    });

    const correlationRows = computed(() => {
      if (!analysis.value?.correlation || !analysis.value?.numeric_columns) {
        return [];
      }

      const corr = analysis.value.correlation;
      return analysis.value.numeric_columns.map((name) => {
        const row = { name };
        analysis.value.numeric_columns.forEach((col) => {
          row[col] = formatNumber(corr[name]?.[col]);
        });
        return row;
      });
    });

    const formatNumber = (value) => {
      if (value === null || value === undefined || Number.isNaN(value)) return "-";
      const num = Number(value);
      if (Number.isNaN(num)) return value;
      return num.toFixed(4);
    };

    const formatCompactNumber = (value) => {
      if (value === null || value === undefined || Number.isNaN(value)) return "-";
      const num = Number(value);
      if (Number.isNaN(num)) return String(value);
      const rounded = Number(num.toFixed(4));
      return Number.isInteger(rounded)
        ? rounded.toLocaleString("zh-CN")
        : rounded.toLocaleString("zh-CN", {
            minimumFractionDigits: 0,
            maximumFractionDigits: 4,
          });
    };

    const formatPercent = (value) => {
      if (value === null || value === undefined || Number.isNaN(value)) return "-";
      const num = Number(value);
      if (Number.isNaN(num)) return value;
      return `${num.toFixed(2)}%`;
    };

    const summarizeChartForAi = () => {
      if (!chartData.value || !currentColumn.value) return "";

      const chartKind = currentColumnKindLabel.value || "图表字段";
      const chartTitle = activeChartPresentation.value?.title || `${currentColumn.value} 图表`;
      const chartType = currentChartTypeLabel.value || "未命名图表";
      const isPieLike = ["pie", "treemap"].includes(chartData.value.type);
      const categories =
        chartData.value.categories ||
        chartData.value.x ||
        [];
      const values =
        chartData.value.values ||
        chartData.value.y ||
        [];

      let detail = "";
      if (isPieLike && Array.isArray(chartData.value.data)) {
        detail = chartData.value.data
          .slice(0, 5)
          .map((item) => `${item.name}：${formatCompactNumber(item.value)}`)
          .join("；");
      } else if (chartData.value.type === "boxplot" && Array.isArray(chartData.value.data?.[0])) {
        const [min, q1, median, q3, max] = chartData.value.data[0];
        detail = `最小值 ${formatCompactNumber(min)}；Q1 ${formatCompactNumber(q1)}；中位数 ${formatCompactNumber(median)}；Q3 ${formatCompactNumber(q3)}；最大值 ${formatCompactNumber(max)}`;
      } else if (Array.isArray(categories) && Array.isArray(values) && categories.length && values.length) {
        detail = categories
          .slice(0, 5)
          .map((label, index) => `${label}：${formatCompactNumber(values[index])}`)
          .join("；");
      }

      return [
        `当前图表标题：${chartTitle}`,
        `图表类型：${chartType}`,
        `图表字段：${currentColumn.value}（${chartKind}）`,
        detail ? `图表摘要：${detail}` : "",
      ]
        .filter(Boolean)
        .join("；");
    };

    const summarizeStatisticsForAi = () => {
      if (!statRows.value.length) return "";

      const topStats = statRows.value
        .slice(0, 4)
        .map(
          (item) =>
            `${item.name}：均值 ${item.mean}，中位数 ${item.median}，最小 ${item.min}，最大 ${item.max}`
        )
        .join("；");

      return `描述性统计摘要：${topStats}`;
    };

    const summarizeCorrelationForAi = () => {
      if (!analysis.value?.correlation || !correlationColumns.value.length) return "";

      let strongestPair = null;
      correlationColumns.value.forEach((rowName, rowIndex) => {
        correlationColumns.value.forEach((columnName, columnIndex) => {
          if (columnIndex <= rowIndex) return;
          const rawValue = Number(analysis.value?.correlation?.[rowName]?.[columnName]);
          if (!Number.isFinite(rawValue)) return;
          const candidate = {
            rowName,
            columnName,
            value: rawValue,
            absValue: Math.abs(rawValue),
          };
          if (!strongestPair || candidate.absValue > strongestPair.absValue) {
            strongestPair = candidate;
          }
        });
      });

      if (!strongestPair) return "";

      return `相关性摘要：${strongestPair.rowName} 与 ${strongestPair.columnName} 的相关系数为 ${formatNumber(strongestPair.value)}，属于 ${getCorrelationStrengthLabel(strongestPair.value)}。`;
    };

    const summarizeGroupByForAi = () => {
      if (!groupByRows.value.length || !groupByColumns.value.length) return "";

      const preview = groupByRows.value
        .slice(0, 3)
        .map((row) =>
          groupByColumns.value
            .map((column) => `${formatGroupByColumnLabel(column) || column}：${row[column]}`)
            .join("，")
        )
        .join("；");

      return `分组统计摘要：共 ${groupByRows.value.length} 行结果，前几行包括 ${preview}`;
    };

    const summarizeDistributionForAi = () => {
      if (!distributionResult.value || !distributionRows.value.length) return "";

      const rows = distributionRows.value
        .slice(0, 5)
        .map(
          (row) =>
            `${row.label}：频数 ${formatCompactNumber(row.frequency)}，占比 ${formatPercent(row.percentage)}`
        )
        .join("；");

      return `频数分布摘要：字段 ${distributionResult.value.column}，前几个区间/类别为 ${rows}`;
    };

    const summarizePredictionForAi = () => {
      if (!predictionResult.value?.forecast?.length) return "";

      const forecast = predictionResult.value.forecast
        .slice(0, 5)
        .map((item) => `${item.label}：${formatCompactNumber(item.value)}`)
        .join("；");

      return `数据预测摘要：目标字段 ${predictionResult.value.target_column}，模型 ${predictionResult.value.model_name}，趋势 ${predictionResult.value.trend}，${predictionResult.value.confidence_label}，未来预测为 ${forecast}`;
    };

    const summarizeQualityForAi = () => {
      if (!qualityReport.value) return "";

      return `数据质量摘要：缺失单元格 ${qualityReport.value.missing_cell_count}，含缺失字段 ${qualityReport.value.columns_with_missing}，重复行 ${qualityReport.value.duplicate_row_count}，候选异常行 ${qualityReport.value.outlier_row_count}。`;
    };

    const summarizeDictionaryForAi = () => {
      if (!fieldProfileReport.value) return "";

      return `字段画像摘要：共 ${fieldProfileReport.value.field_count} 个字段，其中数值字段 ${fieldProfileTypeCounts.value.numeric || 0} 个，类别字段 ${fieldProfileTypeCounts.value.categorical || 0} 个，日期时间字段 ${fieldProfileTypeCounts.value.datetime || 0} 个。`;
    };

    const buildAiCurrentResultPrompt = () => {
      const section = activeWorkspaceSection.value;
      const parts = [];

      if (section === "overview") {
        parts.push(summarizeDictionaryForAi());
      } else if (section === "preparation") {
        parts.push(summarizeQualityForAi());
      } else if (section === "exploration") {
        parts.push(summarizeGroupByForAi());
        parts.push(summarizeDistributionForAi());
      } else if (section === "visualization") {
        parts.push(summarizeChartForAi());
        parts.push(summarizeStatisticsForAi());
        parts.push(summarizeCorrelationForAi());
        parts.push(summarizePredictionForAi());
      } else {
        parts.push(summarizeChartForAi());
        parts.push(summarizeGroupByForAi());
        parts.push(summarizeDistributionForAi());
        parts.push(summarizePredictionForAi());
        parts.push(summarizeQualityForAi());
      }

      const summary = parts.filter(Boolean).join("\n");
      if (!summary) return "";

      return [
        `请用简洁、专业但易懂的中文，解释我当前正在看的分析结果。`,
        `当前文件：${selectedFileDisplay.value || "未命名文件"}`,
        `当前模块：${WORKSPACE_SECTION_OPTIONS.find((item) => item.value === section)?.label || section}`,
        summary,
        `请按以下结构回答：`,
        `1. 这组结果说明了什么`,
        `2. 值得注意的发现`,
        `3. 如果我要展示给别人，应该怎么解释`,
      ].join("\n");
    };

    const buildAiPresentationSummaryPrompt = () => {
      const summaryParts = [
        summarizeDictionaryForAi(),
        summarizeQualityForAi(),
        summarizeGroupByForAi(),
        summarizeDistributionForAi(),
        summarizeChartForAi(),
        summarizeStatisticsForAi(),
        summarizeCorrelationForAi(),
        summarizePredictionForAi(),
      ].filter(Boolean);

      if (!summaryParts.length) return "";

      return [
        `请基于下面这些分析结果，生成一段适合汇报或答辩展示的中文摘要。`,
        `当前文件：${selectedFileDisplay.value || "未命名文件"}`,
        ...summaryParts,
        `请输出以下四部分：`,
        `1. 数据概况`,
        `2. 关键发现`,
        `3. 风险提醒`,
        `4. 推荐展示顺序`,
      ].join("\n");
    };

    const formatOutlierDetail = (column) => {
      const parts = [];
      if (column?.outlier_bounds?.method_label) {
        parts.push(`方式：${column.outlier_bounds.method_label}`);
      }
      if (column?.outlier_bounds?.note) {
        parts.push(column.outlier_bounds.note);
      }
      if (
        column?.outlier_count &&
        column.outlier_bounds &&
        column.outlier_bounds.lower_bound !== undefined &&
        column.outlier_bounds.upper_bound !== undefined
      ) {
        parts.push(
          `检测区间 < ${formatCompactNumber(column.outlier_bounds.lower_bound)} 或 > ${formatCompactNumber(
            column.outlier_bounds.upper_bound
          )}`
        );
      }

      if (column?.outlier_samples?.length) {
        parts.push(
          column.outlier_samples
            .map((item) => `第 ${item.row_index} 行: ${formatCompactNumber(item.value)}`)
            .join("；")
        );
      }

      return parts.join(" | ") || "-";
    };

    const formatConversionTargetLabel = (targetType) => {
      return (
        TYPE_CONVERSION_OPTIONS.find((option) => option.value === targetType)
          ?.label || targetType
      );
    };

    const formatQueryOperatorLabel = (operator) => {
      return (
        QUERY_OPERATOR_OPTIONS.find((option) => option.value === operator)?.label ||
        operator
      );
    };

    const formatQueryFilterLabel = (filter) => {
      const operatorLabel = formatQueryOperatorLabel(filter.operator);

      if (filter.operator === "is_null" || filter.operator === "not_null") {
        return `${filter.column} ${operatorLabel}`;
      }

      if (filter.operator === "between") {
        return `${filter.column} ${operatorLabel} ${filter.value} ~ ${filter.secondValue}`;
      }

      if (filter.operator === "in") {
        return `${filter.column} ${operatorLabel} ${filter.value}`;
      }

      return `${filter.column} ${operatorLabel} ${filter.value}`;
    };

    const formatGroupAggregationLabel = (aggregation) => {
      return (
        GROUP_AGGREGATION_OPTIONS.find((option) => option.value === aggregation)
          ?.label || aggregation
      );
    };

    const formatGroupByColumnLabel = (column) => {
      if (!column) return "";
      if (column === "row_count") return "每组记录数";

      const matchedAggregation = GROUP_AGGREGATION_OPTIONS.find((option) =>
        column.endsWith(`_${option.value}`)
      );

      if (!matchedAggregation) {
        return column;
      }

      const sourceColumn = column.slice(
        0,
        -(matchedAggregation.value.length + 1)
      );

      if (!sourceColumn) {
        return formatGroupAggregationLabel(matchedAggregation.value);
      }

      return `${sourceColumn}·${formatGroupAggregationLabel(
        matchedAggregation.value
      )}`;
    };

    const formatDetectedTypeLabel = (type) => {
      const typeMap = {
        numeric: "数值",
        categorical: "类别",
        datetime: "日期时间",
        empty: "空列",
      };
      return typeMap[type] || type;
    };

    const formatFileSize = (size) => {
      if (size < 1024) return `${size} B`;
      if (size < 1024 * 1024) return `${(size / 1024).toFixed(2)} KB`;
      return `${(size / 1024 / 1024).toFixed(2)} MB`;
    };

    const formatDisplayName = (filename) => {
      const parts = filename.split("_");
      const rawName =
        parts.length > 1 && /^\d+$/.test(parts[0])
          ? parts.slice(1).join("_")
          : filename;

      const dotIndex = rawName.lastIndexOf(".");
      const stem = dotIndex >= 0 ? rawName.slice(0, dotIndex) : rawName;
      const normalizedStem = stem.trim();
      const generatedSuffixMatch = normalizedStem.match(
        /^(.*?)(?:[_-](cleaned|clean|rollback)(\d+)?(?:[_-]\d{1,8}){0,4})$/i
      );

      if (!generatedSuffixMatch) {
        return normalizedStem || rawName;
      }

      const baseName = (generatedSuffixMatch[1] || "")
        .replace(/[_-]+$/, "")
        .trim() || "dataset";
      const suffixType = (generatedSuffixMatch[2] || "").toLowerCase();
      const versionNumber = generatedSuffixMatch[3] ? ` ${generatedSuffixMatch[3]}` : "";
      const versionLabel = suffixType === "rollback" ? "回滚版" : "清洗版";

      return `${baseName} · ${versionLabel}${versionNumber}`;
    };

    const formatDateTime = (value) => {
      if (!value) return "-";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return value;
      return date.toLocaleString("zh-CN", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      });
    };

    const logout = () => {
      localStorage.removeItem("token");
      router.push("/login");
    };

    const handleResize = () => {
      if (chartInstance) {
        chartInstance.resize();
      }
      if (distributionChartInstance) {
        distributionChartInstance.resize();
      }
      if (correlationChartInstance) {
        correlationChartInstance.resize();
      }
      if (predictionChartInstance) {
        predictionChartInstance.resize();
      }
      syncWorkspaceStickyMetrics();
    };

    const syncWorkspaceStickyMetrics = () => {
      const dashboardShell = document.querySelector(".dashboard-shell");
      if (!dashboardShell) return;

      const topbar = document.querySelector(".platform-topbar");
      const sectionBar = document.querySelector(".workspace-section-bar");
      const topbarHeight = topbar?.offsetHeight || 76;
      const sectionBarHeight = sectionBar?.offsetHeight || 112;
      const sidebarTop =
        topbarHeight + WORKSPACE_SECTION_STICKY_TOP + sectionBarHeight + 16;
      const sidebarMaxHeight = Math.max(320, window.innerHeight - sidebarTop - 24);

      dashboardShell.style.setProperty("--workspace-sidebar-top", `${sidebarTop}px`);
      dashboardShell.style.setProperty("--workspace-sidebar-max-height", `${sidebarMaxHeight}px`);
    };

    watch(activeWorkspaceSection, async (section) => {
      await nextTick();

      if (section === "exploration" && distributionResult.value) {
        await renderDistributionChart();
      }

      if (section === "visualization") {
        if (chartData.value) {
          await renderChart();
        }

        if (correlationRows.value.length && correlationView.value === "heatmap") {
          await renderCorrelationHeatmap();
        }

        if (predictionResult.value) {
          await renderPredictionChart();
        }
      }
    });

    watch(
      () => [
        showChartExportPanel.value,
        chartExportForm.value.title,
        chartExportForm.value.xAxisLabel,
        chartExportForm.value.yAxisLabel,
      ],
      async () => {
        if (
          !chartData.value ||
          loadingChart.value ||
          activeWorkspaceSection.value !== "visualization"
        ) {
          return;
        }

        await nextTick();
        await renderChart();
      }
    );

    watch(
      () => [
        predictionResult.value,
        loadingPrediction.value,
        activeWorkspaceSection.value,
      ],
      async () => {
        if (
          !predictionResult.value ||
          loadingPrediction.value ||
          activeWorkspaceSection.value !== "visualization"
        ) {
          return;
        }

        await nextTick();
        await waitForAnimationFrame();
        await renderPredictionChart();
      }
    );

    onMounted(async () => {
      await fetchMe();
      await fetchAiStatus();
      await fetchFiles(true);
      await fetchHistory();
      await fetchDashboardSummary();
      await nextTick();
      syncWorkspaceStickyMetrics();
      window.addEventListener("resize", handleResize);
    });

    onBeforeUnmount(() => {
      window.removeEventListener("resize", handleResize);
      clearChartInstance();
      clearDistributionChartInstance();
      clearCorrelationChartInstance();
      clearPredictionChartInstance();
    });

    const workspaceContext = {
      analysis,
      analysisPlans,
      activeWorkspaceSection,
      aiAssistantForm,
      aiAssistantMessages,
      aiAssistantLastCompletedAt,
      aiAssistantLastError,
      aiAssistantStage,
      aiContextualPrompts,
      aiStatus,
      AI_QUICK_PROMPTS,
      addTypeConversion,
      addQueryFilter,
      addGroupMetric,
      applyAiSuggestedAction,
      applyAnalysisPlan,
      applyingCleaning,
      applyingPlanId,
      applyCleaning,
      cleaningHistory,
      availableDistributionColumns,
      availablePredictionFeatureColumns,
      availablePredictionTargetColumns,
      availableQueryColumns,
      availableGroupColumns,
      availableGroupMetricColumns,
      availableConversionColumns,
      activeChartPresentation,
      chartData,
      chartExportForm,
      chartPanelSubtitle,
      chartRef,
      cancelChartExportPanel,
      changeQueryPage,
      closeAiAssistantDrawer,
      clearAiConversation,
      clearQueryPreview,
      cleaningForm,
      CLEANING_MISSING_OPTIONS,
      CLEANING_OUTLIER_OPTIONS,
      CORRELATION_THRESHOLD_OPTIONS,
      CORRELATION_VIEW_OPTIONS,
      DISTRIBUTION_MODE_OPTIONS,
      DISTRIBUTION_SORT_OPTIONS,
      FIELD_PROFILE_TYPE_OPTIONS,
      GROUP_AGGREGATION_OPTIONS,
      QUERY_OPERATOR_OPTIONS,
      QUERY_SORT_DIRECTION_OPTIONS,
      distributionChartRef,
      distributionForm,
      distributionResult,
      distributionRows,
      predictionChartRef,
      predictionForm,
      predictionResult,
      groupByColumns,
      groupByForm,
      groupByResult,
      groupByRows,
      queryForm,
      queryOperatorNeedsSecondValue,
      queryOperatorNeedsValue,
      queryPreviewColumns,
      queryPreviewResult,
      queryPreviewRows,
      runQueryPreview,
      TYPE_CONVERSION_OPTIONS,
      cleaningPreview,
      cleaningPreviewColumns,
      cleaningPreviewRows,
      correlationAbsThreshold,
      correlationRows,
      correlationChartHeight,
      correlationChartRef,
      correlationView,
      visibleCorrelationPairCount,
      currentChartOptions,
      currentChartType,
      currentChartTypeLabel,
      currentColumn,
      currentColumnKindLabel,
      currentUser,
      deleteFile,
      deleteAnalysisPlan,
      deletingPlanId,
      explainCurrentAnalysisResult,
      expandedOutlierColumn,
      exportingTarget,
      exportChartImage,
      exportCorrelationResult,
      exportDistributionResult,
      exportGroupByResult,
      exportQueryResult,
      exportStatisticsResult,
      fieldDictionaryForm,
      fieldProfileReport,
      fieldProfileTypeCounts,
      filteredFieldProfiles,
      formatCleaningOperationLabels,
      feedbackText,
      feedbackType,
      fillAiQuestion,
      files,
      fetchFiles,
      formatDateTime,
      formatDisplayName,
      formatConversionTargetLabel,
      formatFileSize,
      formatDetectedTypeLabel,
      formatGroupAggregationLabel,
      formatGroupByColumnLabel,
      formatOutlierColumnLabel,
      formatOutlierDetail,
      formatPercent,
      formatQueryFilterLabel,
      formatQueryOperatorLabel,
      generateAiPresentationSummary,
      handleUpload,
      historyRecords,
      isPanelHelpOpen,
      askAiAssistant,
      loadChart,
      loadingAnalysis,
      loadingAiAssistant,
      loadingChart,
      loadingCleaningHistory,
      loadingCleaningPreview,
      loadingDistribution,
      loadingFieldProfiles,
      loadingFiles,
      loadingGroupBy,
      loadingOutlierColumn,
      loadingPrediction,
      loadingPlans,
      loadingPreview,
      loadingQuality,
      loadingQueryPreview,
      logout,
      latestAiAssistantMessage,
      latestAiPresentationMessage,
      openAiAssistantDrawer,
      openChartExportPanel,
      outlierDetailMap,
      planForm,
      previewCleaning,
      previewColumns,
      previewData,
      qualityColumns,
      qualityReport,
      rollbackCleaningHistory,
      removeGroupMetric,
      removeQueryFilter,
      removeTypeConversion,
      runDistributionAnalysis,
      runGroupBy,
      runPrediction,
      saveAnalysisPlan,
      savingPlan,
      selectedFile,
      selectedFileDisplay,
      showAiAssistantDrawer,
      showChartExportPanel,
      panelHelpContent: PANEL_HELP_CONTENT,
      copyAiMessageContent,
      setWorkspaceSection,
      setCorrelationAbsThreshold,
      setGroupAggregation,
      setCorrelationView,
      setMissingStrategy,
      setOutlierStrategy,
      selectChartColumn,
      selectFile,
      jumpToCleaningHistoryFile,
      shouldShowDistributionBins,
      statRows,
      togglePanelHelp,
      toggleAiAssistantDrawer,
      toggleOutlierDetail,
      rollingBackHistoryId,
      WORKSPACE_SECTION_OPTIONS,
    };

    provide("workspaceCtx", proxyRefs(workspaceContext));

    return workspaceContext;
  },
});
