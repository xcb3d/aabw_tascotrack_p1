import { useTranslation } from "react-i18next";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { usePersona } from "@/hooks/use-persona";

export function PersonaSwitcher({ compact = false }: { compact?: boolean }) {
  const { persona, personas, switchPersona } = usePersona(); const { t } = useTranslation();
  return <div className="space-y-1.5"><label className="text-[10px] font-bold uppercase tracking-[.16em] text-muted-foreground">{t("common.role")}</label><Select value={persona?.id ?? ""} onValueChange={(value) => void switchPersona(value)}><SelectTrigger aria-label="Persona" className={compact ? "h-9 max-w-[220px]" : "h-auto min-h-12 border-white/10 bg-white/8 text-white shadow-none hover:bg-white/12"}><SelectValue placeholder="Select persona" /></SelectTrigger><SelectContent className="min-w-[290px]">{personas.map((user) => <SelectItem key={user.id} value={user.id}><span className="flex items-center gap-2"><span className="grid size-7 place-items-center rounded-full bg-secondary text-primary font-bold text-xs">{user.fullName.charAt(0).toUpperCase()}</span><span><span className="block font-semibold">{user.fullName}</span><span className="block text-xs text-muted-foreground">{user.role} · {user.department}</span></span></span></SelectItem>)}</SelectContent></Select></div>;
}
