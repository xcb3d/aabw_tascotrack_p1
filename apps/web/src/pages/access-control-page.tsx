import { useState } from "react";
import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { allPersonas, evaluations } from "@/data";
import { assistantService } from "@/services/mock-services";
import type { AssistantResponse, User } from "@/types";

const matrix = [
  { classification: "Public", Employee: "Allow", Manager: "Allow", Director: "Allow", Executive: "Allow" },
  { classification: "Internal", Employee: "Allow", Manager: "Allow", Director: "Allow", Executive: "Allow" },
  { classification: "Confidential", Employee: "Own", Manager: "Own", Director: "Own", Executive: "Allow" },
  { classification: "Restricted", Employee: "Deny", Manager: "Deny", Director: "Deny", Executive: "Allow" },
];
const comparisonUsers = ["U003", "U004", "U006", "U007"]
  .map((id) => allPersonas.find((user) => user.id === id)!)
  .filter(Boolean);

export function AccessControlPage() {
  const { t } = useTranslation();
  const [question, setQuestion] = useState("Ưu tiên chiến lược của công ty năm 2026 là gì?");
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<{ user: User; response: AssistantResponse }[]>([]);

  const run = async () => {
    setRunning(true);
    const responses = await Promise.all(
      comparisonUsers.map(async (user) => ({
        user,
        response: await assistantService.ask(question, user),
      }))
    );
    setResults(responses);
    setRunning(false);
  };

  return (
    <div>
      <PageHeader eyebrow="RBAC simulator" title={t("access.title")} description={t("access.subtitle")} />

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
        <Card>
          <CardHeader>
            <CardTitle>
              {t("access.matrix")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Classification</TableHead>
                  <TableHead>Employee</TableHead>
                  <TableHead>Manager</TableHead>
                  <TableHead>Director</TableHead>
                  <TableHead>Executive</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {matrix.map((row) => (
                  <TableRow key={row.classification}>
                    <TableCell className="font-bold">{row.classification}</TableCell>
                    {(["Employee", "Manager", "Director", "Executive"] as const).map((role) => (
                      <TableCell key={role}>
                        {row[role] === "Allow" ? (
                          <Badge variant="success">
                            {t("access.allowed")}
                          </Badge>
                        ) : row[role] === "Own" ? (
                          <Badge variant="warning">{t("access.own")}</Badge>
                        ) : (
                          <Badge variant="danger">
                            {t("access.denied")}
                          </Badge>
                        )}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <div className="mt-5 rounded-xl bg-muted/60 p-4 text-sm leading-6 text-muted-foreground">
              <strong className="text-foreground">Decision order:</strong> classification → role → department match.
              Knowledge Admin is deliberately outside this matrix and only controls document administration.
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("access.simulator")}</CardTitle>
          </CardHeader>
          <CardContent>
            <Select value={question} onValueChange={setQuestion}>
              <SelectTrigger className="h-auto min-h-11">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="max-w-xl">
                {evaluations
                  .filter((item) => ["P007", "P009", "P032", "P037", "P042"].includes(item.id))
                  .map((item) => (
                    <SelectItem key={item.id} value={item.question}>
                      {item.question}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
            <Button className="mt-3 w-full font-bold" onClick={() => void run()} disabled={running}>
              {running ? "Evaluating personas..." : t("access.run")}
            </Button>
          </CardContent>
        </Card>
      </div>

      <div className="stagger mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {(results.length ? results : comparisonUsers.map((user) => ({ user, response: null }))).map(
          ({ user, response }) => (
            <Card
              key={user.id}
              className={response?.state === "complete" ? "border-emerald-200" : response ? "border-rose-200" : ""}
            >
              <CardHeader>
                <div className="flex items-center justify-between">
                  <span className="grid size-9 place-items-center rounded-full bg-secondary font-display text-sm font-extrabold text-primary">
                    {user.fullName.split(" ").slice(-1)[0][0]}
                  </span>
                  {response &&
                    (response.state === "complete" ? (
                      <Badge variant="success">Allow</Badge>
                    ) : (
                      <Badge variant="danger">Deny</Badge>
                    ))}
                </div>
                <CardTitle className="pt-3">{user.fullName}</CardTitle>
                <p className="text-xs text-muted-foreground">
                  {user.role} · {user.department}
                </p>
              </CardHeader>
              <CardContent>
                {!response ? (
                  <p className="text-sm text-muted-foreground">
                    Run the comparison to see this persona's permission decision.
                  </p>
                ) : response.state === "complete" ? (
                  <p className="line-clamp-5 text-sm leading-6">{response.answer}</p>
                ) : (
                  <div className="flex gap-2 text-sm leading-6 text-rose-700">
                    <span>{t("assistant.denied")}</span>
                  </div>
                )}
              </CardContent>
            </Card>
          )
        )}
      </div>
    </div>
  );
}
