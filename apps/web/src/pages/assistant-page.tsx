import { useEffect, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/input";
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet";
import { ClassificationBadge } from "@/components/shared/classification-badge";
import { usePersona } from "@/hooks/use-persona";
import { assistantService } from "@/services/mock-services";
import { readStorage, STORAGE_KEYS, writeStorage } from "@/services/storage";
import type { AssistantState, ChatMessage, ChatSession, Citation } from "@/types";
import { cn } from "@/lib/utils";

const suggestions = [
  "Chính sách thử việc là gì?",
  "Nhân viên được bao nhiêu ngày nghỉ phép năm?",
  "Tôi đang thử việc, tôi có được hoàn ứng chi phí công tác không?",
  "Ưu tiên chiến lược của công ty năm 2026 là gì?",
];

function CitationPanel({ citations, onClose }: { citations: Citation[]; onClose?: () => void }) {
  const { t } = useTranslation();
  return (
    <div className="h-full overflow-y-auto">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[.16em] text-primary">Evidence</p>
          <h2 className="font-display text-lg font-bold">{t("common.citations")}</h2>
        </div>
        <Badge variant="secondary">{citations.length}</Badge>
      </div>

      {citations.length === 0 ? (
        <div className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">
          Nguồn của câu trả lời sẽ xuất hiện tại đây.
        </div>
      ) : (
        <div className="stagger space-y-3">
          {citations.map((item, index) => (
            <Card key={item.id} className="overflow-hidden">
              <div className="border-b bg-muted/45 p-4">
                <div className="flex items-start gap-3">
                  <span className="grid size-7 shrink-0 place-items-center rounded-full bg-primary text-xs font-bold text-white">
                    {index + 1}
                  </span>
                  <div className="min-w-0">
                    <p className="font-display text-sm font-bold leading-snug">{item.title}</p>
                    <p className="mt-1 font-mono text-[10px] text-muted-foreground">
                      {item.documentId} · {item.department}
                    </p>
                  </div>
                </div>
              </div>
              <div className="p-4">
                <ClassificationBadge value={item.classification} />
                <p className="mt-3 text-sm leading-6 text-muted-foreground">{item.excerpt}</p>
              </div>
            </Card>
          ))}
        </div>
      )}

      {onClose && (
        <Button variant="outline" className="mt-5 w-full" onClick={onClose}>
          {t("common.close")}
        </Button>
      )}
    </div>
  );
}

export function AssistantPage() {
  const { t } = useTranslation();
  const { persona } = usePersona();
  const [sessions, setSessions] = useState<ChatSession[]>(() =>
    readStorage(STORAGE_KEYS.sessions, [])
  );
  const [activeId, setActiveId] = useState<string>(() => sessions[0]?.id ?? crypto.randomUUID());
  const [question, setQuestion] = useState("");
  const [stage, setStage] = useState<AssistantState | null>(null);
  const [citationOpen, setCitationOpen] = useState(false);

  const active = sessions.find((session) => session.id === activeId);

  const latestCitations = useMemo(() => {
    const lastWithCitations = [...(active?.messages ?? [])]
      .reverse()
      .find((message) => message.response?.citations.length);
    return lastWithCitations?.response?.citations ?? [];
  }, [active]);

  useEffect(() => {
    writeStorage(STORAGE_KEYS.sessions, sessions);
  }, [sessions]);

  const mutation = useMutation({
    mutationFn: ({ prompt }: { prompt: string }) =>
      assistantService.ask(prompt, persona!, setStage),
    onSuccess: (response) => {
      setSessions((items) =>
        items.map((session) =>
          session.id === activeId
            ? {
                ...session,
                updatedAt: new Date().toISOString(),
                messages: [
                  ...session.messages,
                  {
                    id: crypto.randomUUID(),
                    role: "assistant",
                    content: response.answer,
                    response,
                    createdAt: new Date().toISOString(),
                  },
                ],
              }
            : session
        )
      );
      setStage(response.state);
    },
  });

  const submit = (prompt = question) => {
    if (!prompt.trim() || !persona || mutation.isPending) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: prompt.trim(),
      createdAt: new Date().toISOString(),
    };

    if (!active) {
      const session: ChatSession = {
        id: activeId,
        title: prompt.trim().slice(0, 42),
        personaId: persona.id,
        messages: [userMessage],
        updatedAt: new Date().toISOString(),
      };
      setSessions((items) => [session, ...items]);
    } else {
      setSessions((items) =>
        items.map((session) =>
          session.id === activeId
            ? {
                ...session,
                messages: [...session.messages, userMessage],
                updatedAt: new Date().toISOString(),
              }
            : session
        )
      );
    }
    setQuestion("");
    setStage("permission");
    mutation.mutate({ prompt });
  };

  const newChat = () => {
    setActiveId(crypto.randomUUID());
    setStage(null);
    setCitationOpen(false);
  };

  return (
    <div className="-m-4 min-h-[calc(100vh-4rem)] sm:-m-6 lg:-m-8 lg:grid lg:min-h-screen lg:grid-cols-[220px_minmax(420px,1fr)_320px] xl:grid-cols-[240px_minmax(520px,1fr)_360px]">
      <aside className="hidden border-r bg-white/70 p-4 lg:flex lg:flex-col">
        <Button className="w-full justify-start font-bold text-xs" onClick={newChat}>
          Cuộc hội thoại mới
        </Button>
        <div className="mt-6 flex items-center gap-2 px-2 text-xs font-bold uppercase tracking-[.15em] text-muted-foreground">
          {t("assistant.history")}
        </div>
        <div className="mt-2 space-y-1 overflow-y-auto">
          {sessions.map((session) => (
            <button
              key={session.id}
              onClick={() => setActiveId(session.id)}
              className={cn(
                "w-full truncate rounded-lg px-3 py-2.5 text-left text-sm font-medium hover:bg-muted",
                session.id === activeId && "bg-secondary text-secondary-foreground"
              )}
            >
              {session.title}
            </button>
          ))}
          {sessions.length === 0 && (
            <p className="px-3 py-8 text-center text-xs text-muted-foreground">
              Chưa có cuộc trò chuyện
            </p>
          )}
        </div>
      </aside>

      <section className="flex min-h-[calc(100vh-4rem)] min-w-0 flex-col bg-white/35">
        <header className="flex items-center justify-between border-b bg-white/70 px-4 py-3 backdrop-blur-xl sm:px-6">
          <div>
            <h1 className="font-display text-lg font-extrabold">{t("assistant.title")}</h1>
            <p className="hidden text-xs text-muted-foreground sm:block">
              {t("assistant.subtitle")}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {persona && (
              <div className="hidden items-center gap-2 rounded-full border border-slate-200 bg-slate-50/50 px-3 py-1.5 text-xs font-semibold text-slate-700 md:flex">
                <span className="relative flex h-2 size-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex size-2 rounded-full bg-emerald-500"></span>
                </span>
                <span>{persona.fullName}</span>
                <span className="text-slate-300 font-normal">|</span>
                <span className="text-slate-500 font-normal">{persona.role}</span>
              </div>
            )}
            <Button
              variant="outline"
              className="lg:hidden px-2 text-xs font-semibold"
              onClick={() => setCitationOpen(true)}
            >
              Nguồn dẫn
            </Button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-8">
          <div className="mx-auto max-w-3xl">
            {!active?.messages.length ? (
              <div className="flex min-h-[58vh] flex-col items-center justify-center text-center">
                <div className="mb-5 grid size-16 place-items-center rounded-2xl bg-[#dcebef] text-primary shadow-[0_12px_35px_rgba(31,83,104,.16)] font-bold text-2xl">
                  AI
                </div>
                <h2 className="font-display text-2xl font-extrabold">{t("assistant.empty")}</h2>
                <p className="mt-2 max-w-lg text-sm text-muted-foreground">{t("assistant.subtitle")}</p>
                <div className="mt-8 grid w-full gap-2 sm:grid-cols-2">
                  {suggestions.map((item) => (
                    <button
                      key={item}
                      onClick={() => submit(item)}
                      className="rounded-xl border bg-white p-4 text-left text-sm font-semibold shadow-sm transition hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md"
                    >
                      {item}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                {active.messages.map((message) =>
                  message.role === "user" ? (
                    <div key={message.id} className="flex justify-end">
                      <div className="max-w-[85%] rounded-2xl rounded-br-md bg-[#173d4d] px-4 py-3 text-sm leading-6 text-white shadow-sm">
                        {message.content}
                      </div>
                    </div>
                  ) : (
                    <div key={message.id} className="flex gap-3">
                      <div className="mt-1 grid size-8 shrink-0 place-items-center rounded-lg bg-secondary text-primary font-bold text-xs">
                        AI
                      </div>
                      <div className="min-w-0 flex-1 rounded-2xl rounded-tl-md border bg-white p-5 shadow-sm">
                        {message.response?.state === "denied" ? (
                          <div className="flex gap-3 text-rose-700">
                            <div>
                              <p className="font-bold">Access denied</p>
                              <p className="mt-1 text-sm leading-6 text-rose-700/80">
                                {t("assistant.denied")}
                              </p>
                            </div>
                          </div>
                        ) : message.response?.state === "insufficient" ? (
                          <div className="flex gap-3 text-amber-800">
                            <div>
                              <p className="font-bold">Insufficient evidence</p>
                              <p className="mt-1 text-sm leading-6 text-amber-800/80">
                                {t("assistant.insufficient")}
                              </p>
                            </div>
                          </div>
                        ) : (
                          <>
                            <p className="whitespace-pre-line text-sm leading-7">
                              {message.content}
                            </p>
                            {message.response?.citations.map((citation, index) => (
                              <button
                                key={citation.id}
                                className="ml-1 mt-3 inline-flex size-6 items-center justify-center rounded-full bg-secondary text-xs font-bold text-primary hover:bg-accent"
                                onClick={() => setCitationOpen(true)}
                                aria-label={`Citation ${index + 1}`}
                              >
                                {index + 1}
                              </button>
                            ))}
                          </>
                        )}
                      </div>
                    </div>
                  )
                )}

                {mutation.isPending && (
                  <div className="flex gap-3">
                    <div className="mt-1 grid size-8 shrink-0 place-items-center rounded-lg bg-secondary text-primary font-bold text-xs animate-pulse">
                      AI
                    </div>
                    <div className="flex-1 rounded-2xl rounded-tl-md border bg-white p-5">
                      <div className="space-y-3">
                        {(["permission", "searching", "synthesizing", "validating"] as const).map(
                          (item) => {
                            const activeStage = stage === item;
                            const done =
                              ["permission", "searching", "synthesizing", "validating"].indexOf(
                                stage ?? ""
                              ) >
                              ["permission", "searching", "synthesizing", "validating"].indexOf(
                                item
                              );
                            return (
                              <div
                                key={item}
                                className={cn(
                                  "flex items-center gap-3 text-sm transition",
                                  !activeStage && !done && "text-muted-foreground/45",
                                  activeStage && "font-semibold text-primary",
                                  done && "text-emerald-700"
                                )}
                              >
                                <span
                                  className={cn(
                                    "grid size-7 place-items-center rounded-full bg-muted text-xs",
                                    activeStage && "animate-pulse bg-secondary text-primary font-bold",
                                    done && "bg-emerald-50 text-emerald-700 font-bold"
                                  )}
                                >
                                  {done ? "✓" : ["permission", "searching", "synthesizing", "validating"].indexOf(item) + 1}
                                </span>
                                {t(`assistant.stages.${item}`)}
                              </div>
                            );
                          }
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="border-t bg-white/85 p-4 backdrop-blur-xl sm:px-8">
          <div className="mx-auto max-w-3xl">
            <div className="relative rounded-2xl border bg-white p-2 shadow-[0_12px_35px_rgba(30,52,61,.1)]">
              <Textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    submit();
                  }
                }}
                placeholder={t("assistant.placeholder")}
                className="min-h-16 border-0 pr-14 shadow-none focus-visible:outline-none"
              />
              <Button
                size="icon"
                className="absolute bottom-3 right-3 rounded-xl px-3 py-1.5 text-xs font-semibold"
                onClick={() => submit()}
                disabled={!question.trim() || mutation.isPending}
              >
                Gửi
              </Button>
            </div>
            <p className="mt-2 text-center text-[10px] text-muted-foreground">
              AI có thể mắc lỗi. Luôn kiểm tra nguồn tham chiếu trước khi ra quyết định.
            </p>
          </div>
        </div>
      </section>

      <aside className="hidden border-l bg-white/70 p-5 lg:block">
        <CitationPanel citations={latestCitations} />
      </aside>

      <Sheet open={citationOpen} onOpenChange={setCitationOpen}>
        <SheetContent className="overflow-y-auto">
          <SheetTitle className="sr-only">{t("common.citations")}</SheetTitle>
          <SheetDescription className="sr-only">Evidence sources</SheetDescription>
          <CitationPanel citations={latestCitations} onClose={() => setCitationOpen(false)} />
        </SheetContent>
      </Sheet>
    </div>
  );
}
