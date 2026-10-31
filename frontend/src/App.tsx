import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { OverviewPage } from './pages/OverviewPage';
import { PromptAnalysisPage } from './pages/PromptAnalysisPage';
import { SettingsPage } from './pages/SettingsPage';
import { AdvicePage } from './pages/AdvicePage';
import './App.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Data is considered fresh for 5 minutes (no refetch during this time)
      staleTime: 5 * 60 * 1000,
      // Cache data for 30 minutes before garbage collection
      gcTime: 30 * 60 * 1000,
      // Don't refetch on window focus (especially important for expensive LLM calls)
      refetchOnWindowFocus: false,
      // Retry failed requests 1 time (instead of default 3)
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="app-layout">
          <Sidebar />
          <div className="main-content">
            <Header />
            <div className="page-content">
              <Routes>
                <Route path="/" element={<OverviewPage />} />
                <Route path="/prompt-analysis" element={<PromptAnalysisPage />} />
                <Route path="/advice" element={<AdvicePage />} />
                <Route path="/settings" element={<SettingsPage />} />
                {/* 旧ルートは使用状況へリダイレクト */}
                <Route path="/monitoring" element={<Navigate to="/" replace />} />
                <Route path="/token-reflection" element={<Navigate to="/advice" replace />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </div>
          </div>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
