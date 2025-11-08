import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { DashboardPage } from './pages/DashboardPage';
import { MonitoringPage } from './pages/MonitoringPage';
import { TokenReflectionPage } from './pages/TokenReflectionPage';
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
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/monitoring" element={<MonitoringPage />} />
              <Route path="/token-reflection" element={<TokenReflectionPage />} />
            </Routes>
          </div>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
