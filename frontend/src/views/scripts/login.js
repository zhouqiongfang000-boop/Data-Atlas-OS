import { defineComponent, ref } from "vue";
import { NButton, NConfigProvider, NInput } from "naive-ui";
import { useRouter } from "vue-router";

import api from "../../api";

export default defineComponent({
  name: "LoginView",
  components: {
    NButton,
    NConfigProvider,
    NInput,
  },
  setup() {
    const router = useRouter();
    const username = ref("");
    const password = ref("");
    const loading = ref(false);
    const message = ref("");
    const messageType = ref("info");
    const naiveThemeOverrides = {
      common: {
        borderRadius: "18px",
        primaryColor: "#111827",
        primaryColorHover: "#1f2937",
        primaryColorPressed: "#030712",
        primaryColorSuppl: "#111827",
      },
      Input: {
        heightMedium: "58px",
        border: "1px solid rgba(148, 163, 184, 0.28)",
        borderHover: "1px solid rgba(17, 24, 39, 0.42)",
        borderFocus: "1px solid #111827",
        boxShadowFocus: "0 0 0 4px rgba(17, 24, 39, 0.08)",
        color: "rgba(255, 255, 255, 0.78)",
        colorFocus: "#ffffff",
        textColor: "#111827",
        placeholderColor: "#8a98ad",
        caretColor: "#111827",
      },
      Button: {
        heightMedium: "58px",
        borderRadiusMedium: "18px",
        fontWeight: "800",
      },
    };

    const handleLogin = async () => {
      if (!username.value.trim() || !password.value.trim()) {
        message.value = "请先输入用户名和密码";
        messageType.value = "warning";
        return;
      }

      loading.value = true;
      message.value = "";

      try {
        const res = await api.post("/login", {
          username: username.value,
          password: password.value,
        });

        localStorage.setItem("token", res.data.access_token);
        localStorage.setItem("username", res.data.username || username.value.trim());
        localStorage.setItem("role", res.data.role || res.data.user?.role || "user");
        message.value = "登录成功，正在进入系统...";
        messageType.value = "success";

        setTimeout(() => {
          router.push("/home");
        }, 500);
      } catch (error) {
        message.value =
          error.response?.data?.detail ||
          error.response?.data?.msg ||
          "登录失败，请检查账号密码";
        messageType.value = "error";
      } finally {
        loading.value = false;
      }
    };

    const goRegister = () => {
      router.push("/register");
    };

    return {
      username,
      password,
      naiveThemeOverrides,
      loading,
      message,
      messageType,
      handleLogin,
      goRegister,
    };
  },
});
