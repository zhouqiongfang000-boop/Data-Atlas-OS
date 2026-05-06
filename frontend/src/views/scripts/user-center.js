import {
  computed,
  defineComponent,
  nextTick,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
} from "vue";
import { useRouter } from "vue-router";

import api from "../../api";

let echartsLoader = null;

const getEcharts = async () => {
  if (!echartsLoader) {
    echartsLoader = import("echarts");
  }
  return echartsLoader;
};

const DEFAULT_USER = {
  id: null,
  username: "",
  role: "user",
  is_active: true,
  created_at: null,
  last_login_at: null,
};

const DEFAULT_SUMMARY = {
  file_count: 0,
  image_count: 0,
  analysis_count: 0,
  cleaning_count: 0,
  plan_count: 0,
};

const CHART_TYPE_LABELS = {
  histogram: "直方图",
  line: "折线图",
  area: "面积图",
  bar: "柱状图",
  horizontal_bar: "横向柱图",
  pie: "饼图",
  donut: "环形图",
  rose: "玫瑰图",
  treemap: "矩形树图",
  boxplot: "箱线图",
};

const IMAGE_ACTION_LABELS = {
  upload: "图片上传",
  process: "图像处理",
  ocr: "文字识别",
  export: "结果导出",
  rollback: "历史回滚",
};

export default defineComponent({
  name: "UserCenter",
  setup() {
    const router = useRouter();

    const currentUser = ref({ ...DEFAULT_USER });
    const summary = ref({ ...DEFAULT_SUMMARY });
    const savingPassword = ref(false);
    const loading = ref(true);
    const feedbackText = ref("");
    const feedbackType = ref("info");
    const activityChartRef = ref(null);
    const activitySeries = ref([]);
    const recentAnalysis = ref([]);
    const recentImageHistory = ref([]);
    const historyFilter = ref("all");
    const passwordForm = reactive({
      old_password: "",
      new_password: "",
    });
    let activityChartInstance = null;

    const setFeedback = (text, type = "info") => {
      feedbackText.value = text;
      feedbackType.value = type;
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
        hour12: false,
      });
    };

    const formatChartType = (chartType) => CHART_TYPE_LABELS[chartType] || chartType || "图表";

    const formatImageAction = (actionType) =>
      IMAGE_ACTION_LABELS[actionType] || actionType || "图片处理";

    const workspaceMetrics = computed(() => [
      {
        key: "files",
        label: "数据文件",
        value: summary.value.file_count,
        helper: "CSV 与清洗版本",
      },
      {
        key: "images",
        label: "图片资产",
        value: summary.value.image_count,
        helper: "原图与处理结果",
      },
      {
        key: "analysis",
        label: "分析记录",
        value: summary.value.analysis_count,
        helper: "图表生成轨迹",
      },
      {
        key: "cleaning",
        label: "清洗记录",
        value: summary.value.cleaning_count,
        helper: "质量处理链路",
      },
      {
        key: "plans",
        label: "分析方案",
        value: summary.value.plan_count,
        helper: "保存的工作方案",
      },
    ]);

    const combinedActivities = computed(() => {
      const analysisItems = recentAnalysis.value.map((item) => ({
        id: `analysis-${item.id}`,
        kind: "analysis",
        label: "数据分析",
        title: item.file_name || "未命名数据文件",
        detail: `${item.column_name || "-"} · ${formatChartType(item.chart_type)}`,
        created_at: item.created_at,
      }));

      const imageItems = recentImageHistory.value.map((item) => {
        const imageName = item.result_image_name || item.source_image_name || "未命名图片";
        const summaryText = item.operation_summary || formatImageAction(item.action_type);

        return {
          id: `image-${item.id}`,
          kind: "image",
          label: "图片处理",
          title: imageName,
          detail: `${formatImageAction(item.action_type)} · ${summaryText}`,
          created_at: item.created_at,
        };
      });

      return [...analysisItems, ...imageItems]
        .sort((left, right) => new Date(right.created_at || 0) - new Date(left.created_at || 0))
        .slice(0, 12);
    });

    const filteredActivities = computed(() => {
      if (historyFilter.value === "all") return combinedActivities.value;
      return combinedActivities.value.filter((item) => item.kind === historyFilter.value);
    });

    const totalRecentActivity = computed(() =>
      activitySeries.value.reduce((total, item) => total + Number(item.total || 0), 0)
    );

    const busiestDayLabel = computed(() => {
      const busiest = activitySeries.value.reduce(
        (current, item) => (Number(item.total || 0) > Number(current.total || 0) ? item : current),
        { label: "-", total: 0 }
      );

      return busiest.total ? `${busiest.label} · ${busiest.total} 次` : "-";
    });

    const latestActivityTime = computed(() => {
      const latest = combinedActivities.value[0]?.created_at;
      return latest ? formatDateTime(latest) : "-";
    });

    const disposeActivityChart = () => {
      if (activityChartInstance) {
        activityChartInstance.dispose();
        activityChartInstance = null;
      }
    };

    const renderActivityChart = async () => {
      await nextTick();
      if (!activityChartRef.value) return;

      const echarts = await getEcharts();
      if (!activityChartInstance) {
        activityChartInstance = echarts.init(activityChartRef.value);
      }

      const labels = activitySeries.value.map((item) => item.label);
      const filePlanValues = activitySeries.value.map(
        (item) => Number(item.asset || 0) + Number(item.plan || 0)
      );

      activityChartInstance.setOption({
        backgroundColor: "transparent",
        color: ["#3b82f6", "#f59e0b", "#22c55e", "#64748b", "#ef4444"],
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "shadow" },
        },
        legend: {
          top: 0,
          right: 0,
          itemWidth: 10,
          itemHeight: 10,
          textStyle: { color: "#475569" },
        },
        grid: {
          top: 46,
          right: 18,
          bottom: 34,
          left: 38,
        },
        xAxis: {
          type: "category",
          data: labels,
          axisLine: { lineStyle: { color: "#cbd5e1" } },
          axisTick: { show: false },
          axisLabel: { color: "#64748b" },
        },
        yAxis: {
          type: "value",
          minInterval: 1,
          splitLine: { lineStyle: { color: "#e2e8f0" } },
          axisLabel: { color: "#64748b" },
        },
        series: [
          {
            name: "数据分析",
            type: "bar",
            stack: "usage",
            barMaxWidth: 18,
            data: activitySeries.value.map((item) => item.analysis || 0),
          },
          {
            name: "图片处理",
            type: "bar",
            stack: "usage",
            barMaxWidth: 18,
            data: activitySeries.value.map((item) => item.image || 0),
          },
          {
            name: "数据清洗",
            type: "bar",
            stack: "usage",
            barMaxWidth: 18,
            data: activitySeries.value.map((item) => item.cleaning || 0),
          },
          {
            name: "文件与方案",
            type: "bar",
            stack: "usage",
            barMaxWidth: 18,
            data: filePlanValues,
          },
          {
            name: "总频率",
            type: "line",
            smooth: true,
            symbolSize: 7,
            lineStyle: { width: 3 },
            data: activitySeries.value.map((item) => item.total || 0),
          },
        ],
      });
    };

    const resizeActivityChart = () => {
      activityChartInstance?.resize();
    };

    const loadAccount = async () => {
      loading.value = true;
      feedbackText.value = "";

      try {
        const [meRes, summaryRes, activityRes] = await Promise.all([
          api.get("/me"),
          api.get("/account/summary"),
          api.get("/account/activity?limit=10&days=14"),
        ]);

        currentUser.value = { ...DEFAULT_USER, ...meRes.data };
        summary.value = { ...DEFAULT_SUMMARY, ...summaryRes.data };
        recentAnalysis.value = activityRes.data?.recent_analysis || [];
        recentImageHistory.value = activityRes.data?.recent_image_history || [];
        activitySeries.value = activityRes.data?.activity_series || [];
        localStorage.setItem("username", currentUser.value.username || "");
        localStorage.setItem("role", currentUser.value.role || "user");
      } catch (error) {
        setFeedback(error.response?.data?.detail || "账号信息加载失败", "error");
      } finally {
        loading.value = false;
      }
    };

    const changePassword = async () => {
      if (!passwordForm.old_password.trim() || !passwordForm.new_password.trim()) {
        setFeedback("请先填写旧密码和新密码", "warning");
        return;
      }

      if (passwordForm.new_password.trim().length < 6) {
        setFeedback("新密码至少需要 6 位", "warning");
        return;
      }

      savingPassword.value = true;
      feedbackText.value = "";

      try {
        await api.patch("/account/password", {
          old_password: passwordForm.old_password,
          new_password: passwordForm.new_password,
        });
        passwordForm.old_password = "";
        passwordForm.new_password = "";
        setFeedback("密码已更新，下次登录请使用新密码", "success");
      } catch (error) {
        setFeedback(error.response?.data?.detail || "密码更新失败", "error");
      } finally {
        savingPassword.value = false;
      }
    };

    const openDataWorkspace = () => {
      router.push({ path: "/workspace/data", query: { section: "assets" } });
    };

    const openImageWorkspace = () => {
      router.push("/workspace/image");
    };

    onMounted(async () => {
      await loadAccount();
      await renderActivityChart();
      window.addEventListener("resize", resizeActivityChart, { passive: true });
    });

    onBeforeUnmount(() => {
      window.removeEventListener("resize", resizeActivityChart);
      disposeActivityChart();
    });

    return {
      activityChartRef,
      busiestDayLabel,
      changePassword,
      combinedActivities,
      currentUser,
      feedbackText,
      feedbackType,
      filteredActivities,
      formatDateTime,
      historyFilter,
      latestActivityTime,
      loading,
      openDataWorkspace,
      openImageWorkspace,
      passwordForm,
      savingPassword,
      summary,
      totalRecentActivity,
      workspaceMetrics,
    };
  },
});
