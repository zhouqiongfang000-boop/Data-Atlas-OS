import { computed, defineComponent, ref } from "vue";
import { NButton, NConfigProvider, NInput } from "naive-ui";
import { useRouter } from "vue-router";

import api from "../../api";

export default defineComponent({
  name: "RegisterView",
  components: {
    NButton,
    NConfigProvider,
    NInput,
  },
  setup() {
    const router = useRouter();
    const username = ref("");
    const password = ref("");
    const confirmPassword = ref("");
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

    const passwordChecks = computed(() => {
      const value = password.value;
      const hasLowercase = /[a-z]/.test(value);
      const hasUppercase = /[A-Z]/.test(value);
      const hasLetter = /[A-Za-z]/.test(value);
      const hasNumber = /\d/.test(value);
      const hasSpecial = /[^A-Za-z0-9]/.test(value);

      return {
        minLength: value.length >= 6,
        recommendedLength: value.length >= 8,
        letterNumber: hasLetter && hasNumber,
        mixedCase: hasLowercase && hasUppercase,
        special: hasSpecial,
      };
    });

    const passwordStrength = computed(() => {
      if (!password.value) {
        return {
          level: "empty",
          label: "等待输入",
          percent: 0,
        };
      }

      const checks = passwordChecks.value;
      const score =
        Math.min(password.value.length, 8) * 4 +
        (checks.letterNumber ? 25 : 0) +
        (checks.mixedCase ? 22 : 0) +
        (checks.special ? 21 : 0);

      if (
        checks.recommendedLength &&
        checks.letterNumber &&
        checks.mixedCase &&
        checks.special
      ) {
        return {
          level: "strong",
          label: "强",
          percent: 100,
        };
      }

      if (checks.minLength && checks.letterNumber && score >= 65) {
        return {
          level: "medium",
          label: "中",
          percent: Math.min(score, 82),
        };
      }

      return {
        level: "weak",
        label: "弱",
        percent: Math.max(Math.min(score, 48), 14),
      };
    });

    const passwordsMatch = computed(
      () => !confirmPassword.value || password.value === confirmPassword.value
    );

    const handleRegister = async () => {
      if (!username.value.trim() || !password.value.trim() || !confirmPassword.value.trim()) {
        message.value = "请先填写完整的注册信息";
        messageType.value = "warning";
        return;
      }

      if (!passwordChecks.value.minLength) {
        message.value = "密码长度不能少于 6 位";
        messageType.value = "warning";
        return;
      }

      if (!passwordChecks.value.letterNumber) {
        message.value = "密码至少需要同时包含字母和数字";
        messageType.value = "warning";
        return;
      }

      if (password.value !== confirmPassword.value) {
        message.value = "两次输入的密码不一致";
        messageType.value = "warning";
        return;
      }

      loading.value = true;
      message.value = "";

      try {
        await api.post("/register", {
          username: username.value,
          password: password.value,
        });

        message.value = "注册成功，正在跳转到登录页...";
        messageType.value = "success";

        setTimeout(() => {
          router.push("/login");
        }, 700);
      } catch (error) {
        message.value =
          error.response?.data?.detail ||
          error.response?.data?.msg ||
          "注册失败，请稍后重试";
        messageType.value = "error";
      } finally {
        loading.value = false;
      }
    };

    const goLogin = () => {
      router.push("/login");
    };

    return {
      username,
      password,
      confirmPassword,
      naiveThemeOverrides,
      passwordChecks,
      passwordStrength,
      passwordsMatch,
      loading,
      message,
      messageType,
      handleRegister,
      goLogin,
    };
  },
});
