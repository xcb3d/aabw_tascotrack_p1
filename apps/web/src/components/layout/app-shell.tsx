import { useState, type ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { documentService } from "@/services/mock-services";
import { cn } from "@/lib/utils";

import { usePersona } from "@/hooks/use-persona";

const navigation = [
  { to: "/assistant", label: "nav.assistant" },
  { to: "/library", label: "nav.library" },
  { to: "/admin/documents", label: "nav.documents" },
  { to: "/admin/evaluation", label: "nav.evaluation" },
  { to: "/demo/access-control", label: "nav.access" },
];

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { t, i18n } = useTranslation();
  const { persona } = usePersona();
  const logout = () => {
    localStorage.removeItem("tasco-token");
    localStorage.removeItem("tasco-user");
    window.dispatchEvent(new Event("tasco-auth-changed"));
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

  return (
    <div className="flex h-full flex-col bg-[#142a33] text-white">
      <div className="flex items-center gap-3 px-5 py-6">
        <div className="grid size-10 place-items-center rounded-xl bg-[#d2e4e9] text-[#163b4a] font-extrabold text-lg">
          T
        </div>
        <div>
          <p className="font-display text-[15px] font-extrabold leading-tight">MY TASCO</p>
          <p className="text-[10px] font-bold tracking-[.2em] text-slate-400">AI WORKSPACE</p>
        </div>
      </div>
      <nav className="flex-1 space-y-1 px-3">
        {filteredNavigation.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-semibold text-slate-300 transition-colors hover:bg-white/8 hover:text-white",
                isActive && "bg-white/12 text-white"
              )
            }
          >
            <span className="flex-1">{t(item.label)}</span>
          </NavLink>
        ))}
      </nav>
      <div className="space-y-4 border-t border-white/10 p-4">
        {persona && (
          <div className="flex items-center gap-2.5 rounded-lg border border-white/10 bg-white/5 p-3">
            <div className="grid size-8 shrink-0 place-items-center rounded-full bg-[#d2e4e9] text-[#163b4a] font-bold text-sm">
              {persona.fullName.charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <span className="block truncate text-xs font-semibold text-white">{persona.fullName}</span>
              <span className="block truncate text-[10px] text-slate-400">
                {persona.role} · {persona.department}
              </span>
            </div>
          </div>
        )}
        <div className="grid grid-cols-2 gap-2">
          <Button
            variant="ghost"
            size="sm"
            className="justify-center text-slate-300 hover:bg-white/10 hover:text-white"
            onClick={() => {
              const lang = i18n.language === "vi" ? "en" : "vi";
              void i18n.changeLanguage(lang);
              localStorage.setItem("tasco-language", lang);
            }}
          >
            {i18n.language === "vi" ? "English" : "Tiếng Việt"}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="justify-center text-red-300 hover:bg-red-500/20 hover:text-red-200"
            onClick={() => logout()}
          >
            Thoát
          </Button>
        </div>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const { i18n } = useTranslation();
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[264px_1fr]">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[264px] lg:block">
        <SidebarContent />
      </aside>
      <div className="min-w-0 lg:col-start-2">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b bg-white/85 px-4 backdrop-blur-xl lg:hidden">
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" className="px-2 font-semibold text-xs">
                Menu
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-[300px] border-0 p-0">
              <SheetTitle className="sr-only">Navigation</SheetTitle>
              <SidebarContent onNavigate={() => setOpen(false)} />
            </SheetContent>
          </Sheet>
          <div className="font-display text-sm font-extrabold">
            MY TASCO <span className="text-primary">AI</span>
          </div>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              const lang = i18n.language === "vi" ? "en" : "vi";
              void i18n.changeLanguage(lang);
              localStorage.setItem("tasco-language", lang);
            }}
          >
            {i18n.language === "vi" ? "English" : "Tiếng Việt"}
          </Button>
        </header>
        <main className="page-enter mx-auto min-h-screen max-w-[1600px] p-4 sm:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
