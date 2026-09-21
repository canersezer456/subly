import { useEffect, useRef } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { apiPost } from "@/lib/api";
import type { AuthResponse } from "@/lib/types";
import { AppShell } from "@/components/layout/AppShell";
import Home from "@/pages/Home";
import Dashboard from "@/pages/Dashboard";
import Expenses from "@/pages/Expenses";
import Incomes from "@/pages/Incomes";
import Subscriptions from "@/pages/Subscriptions";
import Bills from "@/pages/Bills";
import CalendarPage from "@/pages/CalendarPage";
import BudgetPage from "@/pages/Budget";
import Savings from "@/pages/Savings";
import Assistant from "@/pages/Assistant";
import Gaming from "@/pages/Gaming";
import GamingAdmin from "@/pages/GamingAdmin";
import GamingEarnings from "@/pages/GamingEarnings";
import GamingGame from "@/pages/GamingGame";
import GamingProduct from "@/pages/GamingProduct";
import Household from "@/pages/Household";
import Settings from "@/pages/Settings";

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
        navigate("/", { replace: true });
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
    <Routes>
      <Route path="/" element={<Home />} />
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
  );
}
