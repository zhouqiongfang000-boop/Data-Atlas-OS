import { computed, defineComponent, nextTick, onMounted, onUnmounted, ref } from "vue";
import { gsap } from "gsap";
import { NIcon } from "naive-ui";
import {
  AlertCircleOutline,
  AlbumsOutline,
  AnalyticsOutline,
  ArrowForwardOutline,
  BarChartOutline,
  BrushOutline,
  BuildOutline,
  CheckmarkCircleOutline,
  CloudUploadOutline,
  ColorWandOutline,
  DocumentTextOutline,
  FolderOpenOutline,
  HomeOutline,
  ImagesOutline,
  LayersOutline,
  LogOutOutline,
  PersonCircleOutline,
  RefreshOutline,
  SearchOutline,
  ShieldCheckmarkOutline,
  SparklesOutline,
  TimeOutline,
  TrendingUpOutline,
} from "@vicons/ionicons5";
import { useRoute, useRouter } from "vue-router";

import api from "../../api";

const sparkLines = {
  files: "0,38 18,31 36,28 54,34 72,18 90,22 108,10 120,12",
  images: "0,36 18,27 36,31 54,18 72,22 90,12 108,13 120,6",
  history: "0,35 18,28 36,31 54,21 72,24 90,14 108,15 120,8",
  readiness: "0,34 18,24 36,29 54,18 72,22 90,14 108,16 120,6",
};

export default defineComponent({
  name: "DashboardHomeView",
  components: {
    AlertCircleOutline,
    AlbumsOutline,
    AnalyticsOutline,
    ArrowForwardOutline,
    BarChartOutline,
    BrushOutline,
    BuildOutline,
    CheckmarkCircleOutline,
    CloudUploadOutline,
    ColorWandOutline,
    DocumentTextOutline,
    FolderOpenOutline,
    HomeOutline,
    ImagesOutline,
    LayersOutline,
    LogOutOutline,
    NIcon,
    PersonCircleOutline,
    RefreshOutline,
    SearchOutline,
    ShieldCheckmarkOutline,
    SparklesOutline,
    TimeOutline,
    TrendingUpOutline,
  },
  setup() {
    const router = useRouter();
    const route = useRoute();
    const homeRoot = ref(null);
    const workflowSection = ref(null);
    let matchMediaContext;

    const currentUser = ref({
      username: localStorage.getItem("username") || "",
      role: localStorage.getItem("role") || "user",
    });
    const files = ref([]);
    const images = ref([]);
    const historyRecords = ref([]);
    const dashboardSummary = ref({
      file_count: 0,
      history_count: 0,
      latest_file: null,
    });
    const loading = ref(true);
    const feedbackText = ref("");
    const searchText = ref("");

    function goTo(to) {
      router.push(to);
    }

    function isNavActive(item) {
      return route.path.startsWith(item.match);
    }

    function openDataWorkspace(section = "overview") {
      router.push({ path: "/workspace/data", query: { section } });
    }

    function openImageWorkspace() {
      router.push("/workspace/image");
    }

    function scrollToWorkflow() {
      workflowSection.value?.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    function logout() {
      localStorage.removeItem("token");
      localStorage.removeItem("role");
      localStorage.removeItem("username");
      router.push("/login");
    }

    const normalizedSearch = computed(() => searchText.value.trim().toLowerCase());

    const recentFiles = computed(() => files.value.slice(0, 5));
    const recentImages = computed(() => images.value.slice(0, 5));
    const recentHistory = computed(() => historyRecords.value.slice(0, 5));

    const userInitial = computed(() => {
      const name = currentUser.value?.username || "U";
      return String(name).trim().slice(0, 1).toUpperCase() || "U";
    });

    const workspaceReadiness = computed(() => {
      const signals = [
        Number(dashboardSummary.value.file_count || files.value.length) > 0,
        images.value.length > 0,
        historyRecords.value.length > 0,
        Boolean(currentUser.value?.username),
      ];
      return Math.round((signals.filter(Boolean).length / signals.length) * 100);
    });

    const navItems = computed(() => {
      const items = [
        { key: "home", label: "首页", meta: "工作区概览", icon: HomeOutline, to: "/home", match: "/home" },
        {
          key: "data",
          label: "数据工作台",
          meta: `${dashboardSummary.value.file_count || files.value.length} 个文件`,
          icon: AnalyticsOutline,
          to: "/workspace/data",
          match: "/workspace/data",
        },
        {
          key: "image",
          label: "图片工作室",
          meta: `${images.value.length} 张图片`,
          icon: ImagesOutline,
          to: "/workspace/image",
          match: "/workspace/image",
        },
        {
          key: "account",
          label: "个人中心",
          meta: "账号与历史",
          icon: PersonCircleOutline,
          to: "/account",
          match: "/account",
        },
      ];

      if (currentUser.value?.role === "admin") {
        items.push({
          key: "admin",
          label: "管理后台",
          meta: "用户与平台",
          icon: ShieldCheckmarkOutline,
          to: "/admin",
          match: "/admin",
        });
      }

      return items;
    });

    const featureChips = ["数据清洗", "统计图表", "预测分析", "图片处理", "OCR 识别"];

    const overviewMetrics = computed(() => [
      {
        key: "files",
        label: "数据文件",
        value: dashboardSummary.value.file_count || files.value.length,
        helper: dashboardSummary.value.latest_file ? `最近：${formatDisplayName(dashboardSummary.value.latest_file)}` : "等待上传",
        points: sparkLines.files,
      },
      {
        key: "images",
        label: "图片资产",
        value: images.value.length,
        helper: images.value.length ? "可进入图片工作室继续处理" : "等待上传",
        points: sparkLines.images,
      },
      {
        key: "history",
        label: "分析记录",
        value: dashboardSummary.value.history_count || historyRecords.value.length,
        helper: historyRecords.value.length ? "最近图表已同步" : "暂无图表历史",
        points: sparkLines.history,
      },
      {
        key: "readiness",
        label: "工作区完整度",
        value: `${workspaceReadiness.value}%`,
        helper: "由当前资产状态计算",
        points: sparkLines.readiness,
      },
    ]);

    const dataFunctionCards = [
      {
        key: "upload-preview",
        title: "上传与预览",
        description: "上传 CSV，查看字段、样本数据和文件质量。",
        icon: CloudUploadOutline,
        section: "overview",
      },
      {
        key: "quality-clean",
        title: "质量检查与清洗",
        description: "缺失值、异常值、清洗预览、应用与回滚。",
        icon: CheckmarkCircleOutline,
        section: "preparation",
      },
      {
        key: "explore",
        title: "查询与分组分析",
        description: "筛选预览、分组统计、分布分析和字段画像。",
        icon: LayersOutline,
        section: "exploration",
      },
      {
        key: "chart-export",
        title: "图表、预测与导出",
        description: "生成图表、相关性、预测结果并导出文件。",
        icon: BarChartOutline,
        section: "visualization",
      },
    ];

    const imageFunctionCards = [
      {
        key: "image-upload",
        title: "图片上传与图库",
        description: "上传 PNG、JPG、WEBP、BMP 并管理图片列表。",
        icon: ImagesOutline,
      },
      {
        key: "image-process",
        title: "处理预览与另存",
        description: "调整处理参数，预览并保存处理后的图片。",
        icon: ColorWandOutline,
      },
      {
        key: "image-ocr",
        title: "OCR 识别与导出",
        description: "识别全文、结构化字段、表格并导出文本或 CSV。",
        icon: DocumentTextOutline,
      },
      {
        key: "image-history",
        title: "质量报告与历史回滚",
        description: "查看亮度、对比度、清晰度、主色和处理历史。",
        icon: TimeOutline,
      },
    ];

    const workflowCards = [
      {
        key: "data-flow",
        kicker: "Data Flow",
        title: "从数据开始",
        description: "上传数据后完成清洗、筛选、统计和图表分析，像处理系统文件一样顺滑。",
        steps: ["上传", "清洗", "筛选", "统计", "图表分析"],
        icon: AnalyticsOutline,
        action: () => openDataWorkspace("overview"),
      },
      {
        key: "image-flow",
        kicker: "Image Flow",
        title: "到图像创作",
        description: "将图片上传、智能处理、OCR 和批量增强收进一个可视化工作流。",
        steps: ["智能抠图", "图像增强", "批量处理"],
        icon: ImagesOutline,
        action: openImageWorkspace,
      },
      {
        key: "manage-flow",
        kicker: "Control Center",
        title: "统一管理",
        description: "账号资产、权限管理和系统状态统一汇总，保持管理清晰但不沉重。",
        steps: ["账号资产", "权限管理", "系统监控"],
        icon: ShieldCheckmarkOutline,
        action: () => goTo(currentUser.value?.role === "admin" ? "/admin" : "/account"),
      },
    ];

    const filteredFiles = computed(() => {
      const query = normalizedSearch.value;
      const source = recentFiles.value;
      if (!query) return source;
      return source.filter((file) =>
        `${file.name || ""} ${file.original_name || ""}`.toLowerCase().includes(query)
      );
    });

    const filteredImages = computed(() => {
      const query = normalizedSearch.value;
      const source = recentImages.value;
      if (!query) return source;
      return source.filter((image) =>
        `${image.name || ""} ${image.original_name || ""}`.toLowerCase().includes(query)
      );
    });

    const filteredHistory = computed(() => {
      const query = normalizedSearch.value;
      const source = recentHistory.value;
      if (!query) return source;
      return source.filter((item) =>
        `${item.file_name || ""} ${item.column_name || ""} ${item.chart_type || ""}`
          .toLowerCase()
          .includes(query)
      );
    });

    const nextStepCards = computed(() => {
      if (!files.value.length) {
        return [
          {
            key: "upload-data",
            title: "先上传一个数据文件",
            description: "数据工作台会基于 CSV 生成预览、质量检查和分析入口。",
            icon: CloudUploadOutline,
            action: () => openDataWorkspace("overview"),
          },
          {
            key: "upload-image",
            title: "或处理一张图片",
            description: "图片工作室支持上传、预处理、质量报告和 OCR。",
            icon: ImagesOutline,
            action: openImageWorkspace,
          },
        ];
      }

      const steps = [
        {
          key: "clean-data",
          title: "检查数据质量并清洗",
          description: "对最新数据执行缺失值、异常值和字段质量检查。",
          icon: CheckmarkCircleOutline,
          action: () => openDataWorkspace("preparation"),
        },
        {
          key: "make-chart",
          title: "生成一次图表分析",
          description: "选择数值字段或类别字段，生成图表和统计摘要。",
          icon: BarChartOutline,
          action: () => openDataWorkspace("visualization"),
        },
      ];

      if (images.value.length) {
        steps.push({
          key: "ocr-image",
          title: "识别图片中的文字",
          description: "进入图片工作室，对当前图片执行 OCR 和结构化导出。",
          icon: DocumentTextOutline,
          action: openImageWorkspace,
        });
      } else {
        steps.push({
          key: "add-image",
          title: "补充图片资产",
          description: "上传图片后可以进行处理预览、质量报告和 OCR。",
          icon: ImagesOutline,
          action: openImageWorkspace,
        });
      }

      return steps;
    });

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

    const formatFileSize = (size) => {
      const numericSize = Number(size || 0);
      if (!numericSize) return "0 B";
      if (numericSize < 1024) return `${numericSize} B`;
      if (numericSize < 1024 * 1024) return `${(numericSize / 1024).toFixed(1)} KB`;
      if (numericSize < 1024 * 1024 * 1024) {
        return `${(numericSize / (1024 * 1024)).toFixed(2)} MB`;
      }
      return `${(numericSize / (1024 * 1024 * 1024)).toFixed(2)} GB`;
    };

    function formatDisplayName(name) {
      if (!name) return "";
      const rawName = String(name).replace(/^\d+_/, "");
      const dotIndex = rawName.lastIndexOf(".");
      const stem = dotIndex >= 0 ? rawName.slice(0, dotIndex) : rawName;
      const generatedSuffixMatch = stem.match(
        /^(.*?)(?:[_-](cleaned|clean|rollback)(\d+)?(?:[_-]\d{1,8}){0,4})$/i
      );

      if (!generatedSuffixMatch) {
        return stem || rawName;
      }

      const baseName = (generatedSuffixMatch[1] || "").replace(/[_-]+$/, "").trim() || "dataset";
      const suffixType = (generatedSuffixMatch[2] || "").toLowerCase();
      const versionNumber = generatedSuffixMatch[3] ? ` ${generatedSuffixMatch[3]}` : "";
      const versionLabel = suffixType === "rollback" ? "回滚版" : "清洗版";
      return `${baseName} · ${versionLabel}${versionNumber}`;
    }

    const fetchHomeData = async () => {
      loading.value = true;
      feedbackText.value = "";

      try {
        const [meRes, filesRes, imagesRes, historyRes, summaryRes] = await Promise.all([
          api.get("/me"),
          api.get("/files"),
          api.get("/images"),
          api.get("/history?limit=8"),
          api.get("/dashboard/summary"),
        ]);

        currentUser.value = meRes.data;
        files.value = filesRes.data.files || [];
        images.value = imagesRes.data.images || [];
        historyRecords.value = historyRes.data.records || [];
        dashboardSummary.value = summaryRes.data || dashboardSummary.value;
        localStorage.setItem("username", meRes.data.username || "");
        localStorage.setItem("role", meRes.data.role || "user");
      } catch (error) {
        feedbackText.value = error.response?.data?.detail || "首页数据加载失败，请稍后重试。";
      } finally {
        loading.value = false;
      }
    };

    const runHomeIntro = async () => {
      if (!homeRoot.value) return;
      await nextTick();

      matchMediaContext?.revert();
      matchMediaContext = gsap.matchMedia();
      matchMediaContext.add("(prefers-reduced-motion: reduce)", () => {
        gsap.set("[data-home-animate]", { autoAlpha: 1, clearProps: "transform,filter" });
      }, homeRoot.value);
    };

    onMounted(async () => {
      await fetchHomeData();
      runHomeIntro();
    });

    onUnmounted(() => {
      matchMediaContext?.revert();
    });

    return {
      currentUser,
      dashboardSummary,
      dataFunctionCards,
      featureChips,
      feedbackText,
      fetchHomeData,
      files,
      filteredFiles,
      filteredHistory,
      filteredImages,
      formatDateTime,
      formatDisplayName,
      formatFileSize,
      goTo,
      historyRecords,
      homeRoot,
      imageFunctionCards,
      images,
      isNavActive,
      loading,
      logout,
      navItems,
      nextStepCards,
      openDataWorkspace,
      openImageWorkspace,
      overviewMetrics,
      searchText,
      scrollToWorkflow,
      userInitial,
      workflowCards,
      workflowSection,
      workspaceReadiness,
    };
  },
});
