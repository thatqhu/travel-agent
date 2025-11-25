import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0', // 允许 Docker 外部访问
    port: 5173,
    watch: {
      usePolling: true // 这是一个关键配置！在 Docker Volume 下有时候文件变更检测不到，开启轮询可以解决
    }
  }
})
