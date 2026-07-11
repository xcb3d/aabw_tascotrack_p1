import { lazy, Suspense, useState, useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/app-shell";
import { Skeleton } from "@/components/ui/skeleton";
import { usePersona } from "@/hooks/use-persona";
import { LoginPage } from "@/pages/login-page";

const AssistantPage = lazy(() => import("@/pages/assistant-page").then((module) => ({ default: module.AssistantPage })));
const LibraryPage = lazy(() => import("@/pages/library-page").then((module) => ({ default: module.LibraryPage })));
const DocumentsAdminPage = lazy(() => import("@/pages/documents-admin-page").then((module) => ({ default: module.DocumentsAdminPage })));
const EvaluationPage = lazy(() => import("@/pages/evaluation-page").then((module) => ({ default: module.EvaluationPage })));
const AccessControlPage = lazy(() => import("@/pages/access-control-page").then((module) => ({ default: module.AccessControlPage })));

function PageFallback() { return <div className="space-y-5"><Skeleton className="h-20 w-2/3"/><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 6 }).map((_, index) => <Skeleton key={index} className="h-48 rounded-xl"/>)}</div></div>; }

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem("tasco-token"));

  useEffect(() => {
    const handleAuthChange = () => {
      setToken(localStorage.getItem("tasco-token"));
    };

    window.addEventListener("tasco-auth-changed", handleAuthChange);
    window.addEventListener("storage", handleAuthChange);

    return () => {
      window.removeEventListener("tasco-auth-changed", handleAuthChange);
      window.removeEventListener("storage", handleAuthChange);
    };
  }, []);

  if (!token) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  const { persona } = usePersona();
  const isKnowledgeAdmin = persona?.isAdmin || persona?.role === "Knowledge Admin";
  const isExecutive = persona?.role === "Executive";
  const hasAccessControl = isKnowledgeAdmin || isExecutive;

  return <AppShell><Suspense fallback={<PageFallback/>}><Routes><Route path="/assistant" element={<AssistantPage/>}/><Route path="/library" element={<LibraryPage/>}/><Route path="/admin/documents" element={isKnowledgeAdmin ? <DocumentsAdminPage/> : <Navigate to="/assistant" replace/>}/><Route path="/admin/evaluation" element={isKnowledgeAdmin ? <EvaluationPage/> : <Navigate to="/assistant" replace/>}/><Route path="/demo/access-control" element={hasAccessControl ? <AccessControlPage/> : <Navigate to="/assistant" replace/>}/><Route path="*" element={<Navigate to="/assistant" replace/>}/></Routes></Suspense></AppShell>;
}
