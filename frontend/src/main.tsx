import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from '@/components/ui/sonner'
import './index.css'
import App from './App.tsx'
import { queryClient } from './lib/queryClient'
import { applyTheme, readTheme } from './lib/theme'
import { I18nProvider } from './lib/i18n'
import { CurrencyProvider } from './lib/currency'

applyTheme(readTheme())

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <I18nProvider>
      <CurrencyProvider>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <App />
          </BrowserRouter>
          <Toaster richColors />
        </QueryClientProvider>
      </CurrencyProvider>
    </I18nProvider>
  </StrictMode>,
)

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js'))
}
