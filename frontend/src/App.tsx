import { Suspense, lazy, useEffect, useRef } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { apiPost } from "@/lib/api";
import type { AuthResponse } from "@/lib/types";
import { AppShell } from "@/components/layout/AppShell";

// Route-level code splitting: each page ships as its own chunk, fetched only
// when its route is visited, instead of one ~2.4MB bundle up front. AppShell
// itself stays eager since it's the shell every authenticated route renders.
const Landing = lazy(() => import("@/pages/Landing"));
const Login = lazy(() => import("@/pages/Login"));
const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Expenses = lazy(() => import("@/pages/Expenses"));
const Incomes = lazy(() => import("@/pages/Incomes"));
const Subscriptions = lazy(() => import("@/pages/Subscriptions"));
const Bills = lazy(() => import("@/pages/Bills"));
const CalendarPage = lazy(() => import("@/pages/CalendarPage"));
const BudgetPage = lazy(() => import("@/pages/Budget"));
const Savings = lazy(() => import("@/pages/Savings"));
const Assistant = lazy(() => import("@/pages/Assistant"));
const Gaming = lazy(() => import("@/pages/Gaming"));
const GamingAdmin = lazy(() => import("@/pages/GamingAdmin"));
const GamingEarnings = lazy(() => import("@/pages/GamingEarnings"));
const GamingGame = lazy(() => import("@/pages/GamingGame"));
const GamingProduct = lazy(() => import("@/pages/GamingProduct"));
const Household = lazy(() => import("@/pages/Household"));
const Settings = lazy(() => import("@/pages/Settings"));

function RouteLoading() {
  return (
    <div className="grid min-h-svh place-items-center bg-background" data-testid="route-loading">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
    </div>
  );
}

function AuthCallback() {
  const location = useLocation();
  const navigate = useNavigate();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;
    const sessionId = new URLSearchParams(location.hash.replace(/^#/, "")).get("session_id");
    if (!sessionId) {
      navigate("/", { replace: true });
      return;
    }
    apiPost<AuthResponse>("/auth/google/session", { session_id: sessionId })
      .then(() => { window.location.replace("/dashboard"); })
      .catch(() => {
        toast.error("Google oturumu doğrulanamadı");
        navigate("/login", { replace: true });
      });
  }, [location.hash, navigate]);

  return (
    <main className="grid min-h-svh place-items-center bg-background text-foreground" data-testid="auth-callback-state">
      <div className="text-center">
        <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        <p className="text-sm text-muted-foreground" data-testid="auth-callback-message">Google hesabın bağlanıyor…</p>
      </div>
    </main>
  );
}

export default function App() {
  const location = useLocation();
  if (location.hash.includes("session_id=")) return <AuthCallback />;
  return (
    <Suspense fallback={<RouteLoading />}>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route element={<AppShell />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/expenses" element={<Expenses />} />
          <Route path="/incomes" element={<Incomes />} />
          <Route path="/subscriptions" element={<Subscriptions />} />
          <Route path="/bills" element={<Bills />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/budget" element={<BudgetPage />} />
          <Route path="/savings" element={<Savings />} />
          <Route path="/assistant" element={<Assistant />} />
          <Route path="/gaming" element={<Gaming />} />
          <Route path="/gaming/admin" element={<GamingAdmin />} />
          <Route path="/gaming/kazanc" element={<GamingEarnings />} />
          <Route path="/gaming/games/:slug" element={<GamingGame />} />
          <Route path="/gaming/products/:id" element={<GamingProduct />} />
          <Route path="/household" element={<Household />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Suspense>
  );
}
