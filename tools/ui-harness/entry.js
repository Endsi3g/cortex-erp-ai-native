import { createApp, h } from "vue";
import Conversation from "../apps/cortex_rental/cortex_rental/public/js/cortex_copilot/CopilotConversation.vue";
const messages = window.__MESSAGES__ || [];
createApp({ render: () => h(Conversation, { messages, scroll: false }) }).mount("#app");
