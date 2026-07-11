import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { z } from "zod";
import { PageHeader } from "@/components/shared/page-header";
import { ClassificationBadge } from "@/components/shared/classification-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { departments } from "@/data";
import { usePersona } from "@/hooks/use-persona";
import { documentService } from "@/services/mock-services";
import type { Classification, Document } from "@/types";

const schema = z.object({
  title: z.string().min(3),
  fileName: z.string().min(3),
  department: z.string().min(1),
  classification: z.enum(["Public", "Internal", "Confidential", "Restricted"]),
  tags: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export function DocumentsAdminPage() {
  const { t } = useTranslation();
  const { persona } = usePersona();
  const client = useQueryClient();
  const [uploadOpen, setUploadOpen] = useState(false);
  const [editing, setEditing] = useState<Document | null>(null);

  const documents = useQuery({ queryKey: ["documents"], queryFn: documentService.list });
  const jobs = useQuery({ queryKey: ["jobs"], queryFn: documentService.jobs });

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { title: "", fileName: "", department: "Company", classification: "Internal", tags: "" },
  });
  const uploadDepartment = useWatch({ control: form.control, name: "department" });
  const uploadClassification = useWatch({ control: form.control, name: "classification" });

  const create = useMutation({
    mutationFn: documentService.create,
    onSuccess: async ({ document }) => {
      toast.success(`${document.id} đã được lập chỉ mục`);
      setUploadOpen(false);
      form.reset();
      await client.invalidateQueries();
    },
  });

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Document> }) => documentService.update(id, data),
    onSuccess: async () => {
      toast.success("Metadata đã được cập nhật");
      setEditing(null);
      await client.invalidateQueries();
    },
  });

  const archive = useMutation({
    mutationFn: (id: string) => documentService.archive(id),
    onSuccess: async () => {
      toast.success("Tài liệu đã được lưu trữ");
      await client.invalidateQueries();
    },
  });

  const reset = async () => {
    await documentService.reset();
    toast.success("Đã khôi phục dataset gốc");
    await client.invalidateQueries();
  };

  const submit = form.handleSubmit((values) =>
    create.mutate({ ...values, tags: values.tags?.split(",").map((item) => item.trim()).filter(Boolean) })
  );

  if (!persona?.isAdmin) {
    return (
      <div>
        <PageHeader eyebrow="Governance" title={t("admin.title")} description={t("admin.subtitle")} />
        <Card className="mx-auto mt-16 max-w-xl border-amber-200 bg-amber-50/70">
          <CardContent className="flex flex-col items-center p-10 text-center">
            <div className="mb-5 font-bold text-amber-700">
              YÊU CẦU QUYỀN ADMIN
            </div>
            <h2 className="font-display text-xl font-extrabold">Knowledge Admin required</h2>
            <p className="mt-2 text-sm leading-6 text-amber-900/70">{t("admin.adminOnly")}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        eyebrow="Governance"
        title={t("admin.title")}
        description={t("admin.subtitle")}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => void reset()}>
              {t("common.reset")}
            </Button>
            <Button onClick={() => setUploadOpen(true)}>
              {t("admin.upload")}
            </Button>
          </div>
        }
      />

      <Tabs defaultValue="documents">
        <TabsList>
          <TabsTrigger value="documents">Documents ({documents.data?.length ?? 0})</TabsTrigger>
          <TabsTrigger value="ingestion">
            {t("admin.ingestion")} ({jobs.data?.length ?? 0})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="documents">
          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Document</TableHead>
                  <TableHead>{t("common.department")}</TableHead>
                  <TableHead>{t("common.classification")}</TableHead>
                  <TableHead>{t("common.status")}</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.data?.map((document) => (
                  <TableRow key={document.id} className={document.status === "Archived" ? "opacity-55" : ""}>
                    <TableCell>
                      <p className="font-semibold">{document.title}</p>
                      <p className="font-mono text-[10px] text-muted-foreground">{document.id}</p>
                    </TableCell>
                    <TableCell>{document.department}</TableCell>
                    <TableCell>
                      <ClassificationBadge value={document.classification} />
                    </TableCell>
                    <TableCell>
                      <Badge variant={document.status === "Archived" ? "secondary" : "success"}>
                        {document.status === "Archived" ? t("common.archived") : t("common.active")}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex justify-end gap-1">
                        <Button size="sm" variant="ghost" onClick={() => setEditing(document)}>
                          {t("admin.edit")}
                        </Button>
                        {document.status !== "Archived" && (
                          <Button size="sm" variant="ghost" className="text-rose-600" onClick={() => archive.mutate(document.id)}>
                            {t("admin.archive")}
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>

        <TabsContent value="ingestion">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {jobs.data?.length ? (
              jobs.data.map((job) => (
                <Card key={job.id}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <Badge variant="success">{t(`admin.${job.status}`)}</Badge>
                    </div>
                    <CardTitle className="pt-3">{job.fileName}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="font-mono text-xs text-muted-foreground">{job.documentId}</p>
                    <div className="mt-4 h-2 rounded-full bg-muted">
                      <div className="h-full rounded-full bg-emerald-500" style={{ width: `${job.progress}%` }} />
                    </div>
                  </CardContent>
                </Card>
              ))
            ) : (
              <Card className="col-span-full border-dashed">
                <CardContent className="py-16 text-center text-sm text-muted-foreground">
                  Chưa có Ingestion Job nào trong phiên demo.
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>
      </Tabs>

      <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("admin.upload")}</DialogTitle>
            <DialogDescription>Tạo một tài liệu demo và mô phỏng pipeline ingestion.</DialogDescription>
          </DialogHeader>
          <form onSubmit={submit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="fileName">{t("admin.file")}</Label>
              <Input id="fileName" placeholder="policy-2026.pdf" {...form.register("fileName")} />
              {form.formState.errors.fileName && <p className="text-xs text-rose-600">Tên tệp là bắt buộc.</p>}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="title">{t("admin.titleField")}</Label>
              <Input id="title" {...form.register("title")} />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>{t("common.department")}</Label>
                <Select value={uploadDepartment} onValueChange={(value) => form.setValue("department", value)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {departments.map((item) => (
                      <SelectItem key={item.id} value={item.name === "Human Resources" ? "HR" : item.name}>
                        {item.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>{t("common.classification")}</Label>
                <Select value={uploadClassification} onValueChange={(value) => form.setValue("classification", value as Classification)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(["Public", "Internal", "Confidential", "Restricted"] as Classification[]).map((item) => (
                      <SelectItem key={item} value={item}>
                        {item}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="tags">Tags</Label>
              <Input id="tags" placeholder="policy, finance, 2026" {...form.register("tags")} />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setUploadOpen(false)}>
                {t("common.cancel")}
              </Button>
              <Button type="submit" disabled={create.isPending}>
                {create.isPending ? "Indexing..." : t("admin.upload")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(editing)} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogContent>
          {editing && (
            <>
              <DialogHeader>
                <DialogTitle>{t("admin.edit")}</DialogTitle>
                <DialogDescription>
                  {editing.id} · {editing.title}
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div className="space-y-1.5">
                  <Label>{t("admin.titleField")}</Label>
                  <Input defaultValue={editing.title} onChange={(event) => setEditing({ ...editing, title: event.target.value })} />
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-1.5">
                    <Label>{t("common.department")}</Label>
                    <Select value={editing.department} onValueChange={(value) => setEditing({ ...editing, department: value })}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {departments.map((item) => (
                          <SelectItem key={item.id} value={item.name === "Human Resources" ? "HR" : item.name}>
                            {item.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <Label>{t("common.classification")}</Label>
                    <Select value={editing.classification} onValueChange={(value) => setEditing({ ...editing, classification: value as Classification })}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {(["Public", "Internal", "Confidential", "Restricted"] as Classification[]).map((item) => (
                          <SelectItem key={item} value={item}>
                            {item}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setEditing(null)}>
                  {t("common.cancel")}
                </Button>
                <Button onClick={() => update.mutate({ id: editing.id, data: { title: editing.title, department: editing.department, classification: editing.classification } })}>
                  {t("common.save")}
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
