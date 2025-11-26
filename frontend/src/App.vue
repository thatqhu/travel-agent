<script setup>
import { ref } from 'vue'

const inputMsg = ref('')
const chatHistory = ref([])
const isProcessing = ref(false)

const sendMessage = async () => {
  if (!inputMsg.value) return

  chatHistory.value.push({ role: 'user', content: inputMsg.value })
  const userMsg = inputMsg.value
  inputMsg.value = ''
  isProcessing.value = true

  const aiMsgIndex = chatHistory.value.push({ role: 'ai', content: '' }) - 1

  // Setup SSE connection
  const eventSource = new EventSource(`http://localhost:8000/chat/stream?message=${encodeURIComponent(userMsg)}`)

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data)

    if (data.type === 'token') {
      chatHistory.value[aiMsgIndex].content += data.content
    } else if (data.type === 'tool') {
      chatHistory.value[aiMsgIndex].content += `\n[${data.content}]\n\n`
    }else if (data.type === 'done') {
      chatHistory.value[aiMsgIndex].content += `\n[${data.content}]\n\n`
      eventSource.close()
      isProcessing.value = false
      return
    }
  }

  eventSource.onerror = () => {
    eventSource.close()
    isProcessing.value = false
    chatHistory.value[aiMsgIndex].content += '\n[Connection Error]'
  }
}
</script>

<template>
  <div class="container">
    <div class="chat-window">
      <div v-for="(msg, index) in chatHistory" :key="index" :class="['message', msg.role]">
        <div class="bubble">
          <span style="white-space: pre-wrap;">{{ msg.content }}</span>
        </div>
      </div>
    </div>
    <div class="input-area">
      <input v-model="inputMsg" @keyup.enter="sendMessage" :disabled="isProcessing" placeholder="请直接输入地点,我将为你安排行程..." />
      <button @click="sendMessage" :disabled="isProcessing">发送</button>
    </div>
  </div>
</template>

<style scoped>
/* 简单样式，确保能看清 */
.container { max-width: 800px; margin: 0 auto; display: flex; flex-direction: column; height: 90vh; }
.chat-window { flex: 1; overflow-y: auto; padding: 20px; border: 1px solid #ccc; margin-bottom: 10px; }
.message { margin-bottom: 10px; display: flex; }
.message.user { justify-content: flex-end; }
.message.ai { justify-content: flex-start; }
.bubble { padding: 10px 15px; border-radius: 10px; max-width: 70%; }
.user .bubble { background: #007bff; color: white; }
.ai .bubble { background: #f1f1f1; color: black; }
.input-area { display: flex; gap: 10px; }
input { flex: 1; padding: 10px; }
</style>
