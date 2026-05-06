import { defineComponent, onMounted, reactive, ref } from "vue";

import api from "../../api";

const DEFAULT_SUMMARY = {
  total_users: 0,
  active_users: 0,
  disabled_users: 0,
  admin_users: 0,
  file_count: 0,
  image_count: 0,
  analysis_count: 0,
};

export default defineComponent({
  name: "AdminDashboard",
  setup() {
    const users = ref([]);
    const summary = ref({ ...DEFAULT_SUMMARY });
    const searchKeyword = ref("");
    const loading = ref(false);
    const updatingUserId = ref(null);
    const feedbackText = ref("");
    const feedbackType = ref("info");
    const passwordDrafts = reactive({});
    const currentUsername = ref(localStorage.getItem("username") || "");

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

    const isSelf = (user) => user.username === currentUsername.value;

    const loadSummary = async () => {
      const res = await api.get("/admin/summary");
      summary.value = { ...DEFAULT_SUMMARY, ...res.data };
    };

    const loadUsers = async () => {
      loading.value = true;
      feedbackText.value = "";

      try {
        const params = {};
        if (searchKeyword.value.trim()) {
          params.q = searchKeyword.value.trim();
        }
        const res = await api.get("/admin/users", { params });
        users.value = res.data.users || [];
      } catch (error) {
        setFeedback(error.response?.data?.detail || "用户列表加载失败", "error");
      } finally {
        loading.value = false;
      }
    };

    const loadAdminData = async () => {
      loading.value = true;
      feedbackText.value = "";

      try {
        const [summaryRes, usersRes, meRes] = await Promise.all([
          api.get("/admin/summary"),
          api.get("/admin/users"),
          api.get("/me"),
        ]);

        summary.value = { ...DEFAULT_SUMMARY, ...summaryRes.data };
        users.value = usersRes.data.users || [];
        currentUsername.value = meRes.data.username || currentUsername.value;
        localStorage.setItem("username", currentUsername.value);
        localStorage.setItem("role", meRes.data.role || "user");
      } catch (error) {
        setFeedback(error.response?.data?.detail || "管理员数据加载失败", "error");
      } finally {
        loading.value = false;
      }
    };

    const patchUser = async (user, payload, successMessage) => {
      updatingUserId.value = user.id;
      feedbackText.value = "";

      try {
        const res = await api.patch(`/admin/users/${user.id}`, payload);
        const updatedUser = res.data.user;
        users.value = users.value.map((item) => (item.id === updatedUser.id ? updatedUser : item));
        await loadSummary();
        setFeedback(successMessage, "success");
        return true;
      } catch (error) {
        setFeedback(error.response?.data?.detail || "用户信息更新失败", "error");
        return false;
      } finally {
        updatingUserId.value = null;
      }
    };

    const toggleUserStatus = (user) => {
      patchUser(
        user,
        { is_active: !user.is_active },
        user.is_active ? "账号已禁用" : "账号已启用"
      );
    };

    const toggleUserRole = (user) => {
      const nextRole = user.role === "admin" ? "user" : "admin";
      patchUser(
        user,
        { role: nextRole },
        nextRole === "admin" ? "已设为管理员" : "已设为普通用户"
      );
    };

    const resetPassword = async (user) => {
      const password = (passwordDrafts[user.id] || "").trim();
      if (password.length < 6) {
        setFeedback("新密码至少需要 6 位", "warning");
        return;
      }

      const updated = await patchUser(user, { password }, "密码已重置");
      if (updated) {
        passwordDrafts[user.id] = "";
      }
    };

    onMounted(loadAdminData);

    return {
      feedbackText,
      feedbackType,
      formatDateTime,
      isSelf,
      loadAdminData,
      loadUsers,
      loading,
      passwordDrafts,
      resetPassword,
      searchKeyword,
      summary,
      toggleUserRole,
      toggleUserStatus,
      updatingUserId,
      users,
    };
  },
});
