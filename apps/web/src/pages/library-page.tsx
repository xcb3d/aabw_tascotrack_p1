import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/shared/page-header";
import { ClassificationBadge } from "@/components/shared/classification-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { departments } from "@/data";
import { usePersona } from "@/hooks/use-persona";
import { documentService, permissionService } from "@/services/mock-services";
import type { Classification, Document } from "@/types";
import { formatDate, normalizeText } from "@/lib/utils";

function DocumentContent({ content }: { content: string }) {
  return (
    <div className="space-y-3 text-sm leading-7 text-slate-700">
      {content
        .split("\n")
        .filter(Boolean)
        .map((line, index) =>
          line.startsWith("# ") ? (
            <h2 key={index} className="font-display text-xl font-extrabold text-foreground">
              {line.slice(2)}
            </h2>
          ) : line.startsWith("## ") ? (
            <h3 key={index} className="pt-3 font-display text-base font-bold text-foreground">
              {line.slice(3)}
            </h3>
          ) : line.startsWith("### ") ? (
            <h4 key={index} className="pt-2 font-semibold text-foreground">
              {line.slice(4)}
            </h4>
          ) : (
            <p key={index}>{line}</p>
          )
        )}
    </div>
  );
}

export function LibraryPage() {
  const { t, i18n } = useTranslation();
  const { persona } = usePersona();
  const [search, setSearch] = useState("");
  const [department, setDepartment] = useState("all");
  const [classification, setClassification] = useState("all");
  const [selected, setSelected] = useState<Document | null>(null);
  const [locked, setLocked] = useState<Document | null>(null);

  const query = useQuery({ queryKey: ["documents"], queryFn: documentService.list });

  const filtered = useMemo(
    () =>
      (query.data ?? []).filter(
        (document) =>
          document.status !== "Archived" &&
          (department === "all" ||
            document.department === department ||
            (department === "Human Resources" && document.department === "HR")) &&
          (classification === "all" || document.classification === classification) &&
          (!search ||
            normalizeText(`${document.id} ${document.title} ${document.metadata.tags.join(" ")}`).includes(
              normalizeText(search)
            ))
      ),
    [query.data, search, department, classification]
  );

  const openDocument = async (document: Document) => {
    if (persona && permissionService.check(persona, document).allowed) {
      const fullDoc = await documentService.get(document.id, persona);
      setSelected(fullDoc || document);
    } else {
      setLocked(document);
    }
  };


  const clear = () => {
    setSearch("");
    setDepartment("all");
    setClassification("all");
  };

  return (
    <div>
      <PageHeader
        eyebrow="Knowledge base"
        title={t("library.title")}
        description={t("library.subtitle")}
        actions={
          <Badge variant="secondary" className="h-8 px-3">
            {filtered.length} / 40 {t("common.documents")}
          </Badge>
        }
      />

      <Card className="mb-5">
        <CardContent className="grid gap-3 p-4 md:grid-cols-[1fr_220px_190px_auto]">
          <div className="relative">
            <Input
              aria-label={t("common.search")}
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={`${t("common.search")} ID, tiêu đề, tag...`}
              className="pl-3"
            />
          </div>
          <Select value={department} onValueChange={setDepartment}>
            <SelectTrigger aria-label={t("common.department")}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">
                {t("common.all")} {t("common.department").toLowerCase()}
              </SelectItem>
              {departments.map((item) => (
                <SelectItem key={item.id} value={item.name}>
                  {i18n.language === "vi" ? item.nameVi : item.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={classification} onValueChange={setClassification}>
            <SelectTrigger aria-label={t("common.classification")}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">
                {t("common.all")} {t("common.classification").toLowerCase()}
              </SelectItem>
              {(["Public", "Internal", "Confidential", "Restricted"] as Classification[]).map((item) => (
                <SelectItem key={item} value={item}>
                  {item}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="ghost" onClick={clear}>
            Clear
          </Button>
        </CardContent>
      </Card>

      {query.isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 9 }).map((_, index) => (
            <Skeleton key={index} className="h-52 rounded-xl" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <Card className="border-dashed py-20 text-center">
          <p className="font-semibold text-muted-foreground">{t("library.noResults")}</p>
        </Card>
      ) : (
        <div className="stagger grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {filtered.map((document) => {
            const allowed = persona ? permissionService.check(persona, document).allowed : false;
            return (
              <button
                key={document.id}
                onClick={() => openDocument(document)}
                className="group min-h-52 rounded-xl border bg-white p-5 text-left shadow-[0_8px_28px_rgba(35,55,63,.05)] transition hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-lg"
              >
                <div className="flex items-start justify-between gap-4">
                  <span className="text-[10px] font-bold text-primary uppercase">
                    Tài liệu
                  </span>
                </div>
                <p className="mt-5 font-mono text-[10px] font-bold tracking-wider text-muted-foreground">
                  {document.id}
                </p>
                <h2 className="mt-1 font-display text-base font-bold leading-snug group-hover:text-primary">
                  {document.title}
                </h2>
                <div className="mt-4 flex flex-wrap gap-2">
                  <ClassificationBadge value={document.classification} />
                  <Badge variant="outline">{document.department}</Badge>
                </div>
                <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
                  <span>Cập nhật: {formatDate(document.metadata.lastUpdated, i18n.language)}</span>
                </div>
              </button>
            );
          })}
        </div>
      )}

      <Dialog open={Boolean(selected)} onOpenChange={(open) => !open && setSelected(null)}>
        <DialogContent className="max-h-[90vh] max-w-3xl overflow-y-auto">
          {selected && (
            <>
              <DialogHeader>
                <div className="mb-3 flex flex-wrap gap-2">
                  <ClassificationBadge value={selected.classification} />
                  <Badge variant="outline">{selected.department}</Badge>
                  <Badge variant="secondary">{selected.id}</Badge>
                </div>
                <DialogTitle>{selected.title}</DialogTitle>
                <DialogDescription>
                  {selected.metadata.wordCount} words · {formatDate(selected.metadata.lastUpdated, i18n.language)}
                </DialogDescription>
              </DialogHeader>
              <DocumentContent content={selected.content} />
            </>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(locked)} onOpenChange={(open) => !open && setLocked(null)}>
        <DialogContent className="max-w-md text-center">
          <div className="mx-auto mb-4 font-bold text-rose-600">
            KHÓA TRUY CẬP
          </div>
          <DialogHeader>
            <DialogTitle>Access denied</DialogTitle>
            <DialogDescription>{t("assistant.denied")}</DialogDescription>
          </DialogHeader>
          <p className="text-xs text-muted-foreground">
            {locked?.classification} · {locked?.department}
          </p>
          <Button className="mt-5" onClick={() => setLocked(null)}>
            {t("common.close")}
          </Button>
        </DialogContent>
      </Dialog>
    </div>
  );
}
