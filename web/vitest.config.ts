import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// Frontend interaction tests (Vitest + Testing Library, jsdom). The API is replaced by a fake fetch in each test,
// so these tests check the UI's behaviour - they do not prove that the live backend or external feeds work.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    include: ['tests/**/*.test.{ts,tsx}'],
    setupFiles: ['tests/setup.ts'],
    css: false,
    restoreMocks: true,
  },
})
