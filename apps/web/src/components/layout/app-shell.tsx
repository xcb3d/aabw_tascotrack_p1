import { useState, type ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { BookOpen, Bot, ChevronRight, FlaskConical, Languages, LogOut, Menu, RotateCcw, Shield, Sparkles, UploadCloud } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { PersonaSwitcher } from "@/components/shared/persona-switcher";
import { documentService } from "@/services/mock-services";
import { cn } from "@/lib/utils";

import { usePersona } from "@/hooks/use-persona";

const navigation = [
  { to: "/assistant", label: "nav.assistant", icon: Bot },
  { to: "/library", label: "nav.library", icon: BookOpen },
  { to: "/admin/documents", label: "nav.documents", icon: UploadCloud },
  { to: "/admin/evaluation", label: "nav.evaluation", icon: FlaskConical },
  { to: "/demo/access-control", label: "nav.access", icon: Shield },
];

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { t, i18n } = useTranslation();
  const { persona } = usePersona();
  const reset = async () => { await documentService.reset(); window.dispatchEvent(new Event("tasco-reset")); };
  const logout = () => {
    localStorage.removeItem("tasco-token");
    localStorage.removeItem("tasco-user");
    window.location.href = "/login";
  };

  const filteredNavigation = navigation.filter((item) => {
    if (item.to.startsWith("/admin/")) {
      return persona?.isAdmin || persona?.role === "Knowledge Admin";
    }
    if (item.to === "/demo/access-control") {
      return persona?.isAdmin || persona?.role === "Knowledge Admin" || persona?.role === "Executive";
    }
    return true;
  });

  return <div className="flex h-full flex-col bg-[#142a33] text-white"><div className="flex items-center gap-3 px-5 py-6"><div className="grid size-10 place-items-center rounded-xl bg-[#d2e4e9] text-[#163b4a]"><Sparkles className="size-5"/></div><div><p className="font-display text-[15px] font-extrabold leading-tight">MY TASCO</p><p className="text-[10px] font-bold tracking-[.2em] text-slate-400">AI WORKSPACE</p></div></div><nav className="flex-1 space-y-1 px-3">{filteredNavigation.map((item) => <NavLink key={item.to} to={item.to} onClick={onNavigate} className={({ isActive }) => cn("group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-semibold text-slate-300 transition-colors hover:bg-white/8 hover:text-white", isActive && "bg-white/12 text-white")}><item.icon className="size-[18px]"/><span className="flex-1">{t(item.label)}</span><ChevronRight className="size-3.5 opacity-0 transition-opacity group-hover:opacity-70"/></NavLink>)}</nav><div className="space-y-4 border-t border-white/10 p-4"><PersonaSwitcher/><div className="grid grid-cols-3 gap-1"><Button variant="ghost" size="sm" className="px-1 text-[11px] justify-start text-slate-300 hover:bg-white/10 hover:text-white" onClick={() => { const lang = i18n.language === "vi" ? "en" : "vi"; void i18n.changeLanguage(lang); localStorage.setItem("tasco-language", lang); }}><Languages className="size-3.5"/> {i18n.language === "vi" ? "EN" : "VI"}</Button><Button variant="ghost" size="sm" className="px-1 text-[11px] justify-start text-slate-300 hover:bg-white/10 hover:text-white" onClick={() => void reset()}><RotateCcw className="size-3.5"/> Reset</Button><Button variant="ghost" size="sm" className="px-1 text-[11px] justify-start text-red-300 hover:bg-red-500/20 hover:text-red-200" onClick={() => logout()}><LogOut className="size-3.5"/> Thoát</Button></div></div></div>;
}

export function AppShell({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false); const { i18n } = useTranslation();
  return <div className="min-h-screen lg:grid lg:grid-cols-[264px_1fr]"><aside className="fixed inset-y-0 left-0 z-30 hidden w-[264px] lg:block"><SidebarContent/></aside><div className="min-w-0 lg:col-start-2"><header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b bg-white/85 px-4 backdrop-blur-xl lg:hidden"><Sheet open={open} onOpenChange={setOpen}><SheetTrigger asChild><Button size="icon" variant="ghost"><Menu/><span className="sr-only">Menu</span></Button></SheetTrigger><SheetContent side="left" className="w-[300px] border-0 p-0"><SheetTitle className="sr-only">Navigation</SheetTitle><SidebarContent onNavigate={() => setOpen(false)}/></SheetContent></Sheet><div className="font-display text-sm font-extrabold">MY TASCO <span className="text-primary">AI</span></div><Button size="sm" variant="ghost" onClick={() => { const lang = i18n.language === "vi" ? "en" : "vi"; void i18n.changeLanguage(lang); localStorage.setItem("tasco-language", lang); }}><Languages/> {i18n.language === "vi" ? "EN" : "VI"}</Button></header><main className="page-enter mx-auto min-h-screen max-w-[1600px] p-4 sm:p-6 lg:p-8">{children}</main></div></div>;
}
