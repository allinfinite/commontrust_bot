import Link from "next/link";

import { escapePbString } from "@/lib/pocketbase";
import { pbAdminList, pbAdminPatch } from "@/lib/pocketbase_admin";
import { formatDate, memberLabel } from "@/lib/ui";

type Member = { id: string; username?: string; display_name?: string; telegram_id?: number };
type Report = {
  id: string;
  collectionId: string;
  description: string;
  evidence_photos?: string[];
  forwarded_messages?: unknown[];
  status: string;
  ai_severity?: number;
  ai_summary?: string;
  ai_recommendation?: string;
  ai_reasoning?: string;
  ai_model_used?: string;
  admin_decision?: string;
  admin_note?: string;
  resolved_at?: string;
  created_at?: string;
  expand?: {
    reporter_id?: Member;
    reported_id?: Member;
  };
};

export const dynamic = "force-dynamic";

async function resolveReportAction(formData: FormData) {
  "use server";
  const id = String(formData.get("id") ?? "");
  const action = String(formData.get("action") ?? "");
  const reportedMemberId = String(formData.get("reported_member_id") ?? "");
  if (!id || !action) return;

  const now = new Date().toISOString();

  if (action === "confirm_scammer") {
    await pbAdminPatch("reports", id, {
      status: "approved",
      admin_decision: "confirm_scammer",
      resolved_at: now
    });
    if (reportedMemberId) {
      await pbAdminPatch("members", reportedMemberId, {
        scammer: true,
        scammer_at: now
      });
    }
  } else if (action === "warn") {
    await pbAdminPatch("reports", id, {
      status: "approved",
      admin_decision: "warn",
      resolved_at: now
    });
  } else if (action === "dismiss") {
    await pbAdminPatch("reports", id, {
      status: "dismissed",
      admin_decision: "dismiss",
      resolved_at: now
    });
  }
}

function severityColor(severity: number): string {
  if (severity >= 7) return "var(--bad)";
  if (severity >= 4) return "var(--accent)";
  return "var(--good)";
}

function pbFileUrl(collectionId: string, recordId: string, filename: string): string {
  const base = (process.env.POCKETBASE_URL ?? "http://localhost:8090").replace(/\/+$/, "");
  return `${base}/api/files/${collectionId}/${recordId}/${filename}`;
}

export default async function AdminReportsPage(props: {
  searchParams?: Promise<{ page?: string; status?: string }>;
}) {
  const sp = (await props.searchParams) ?? {};
  const page = Math.max(1, Number(sp.page ?? "1") || 1);
  const status = (sp.status ?? "").trim();

  const filter = status ? `status='${escapePbString(status)}'` : undefined;

  const reports = await pbAdminList<Report>("reports", {
    page,
    perPage: 30,
    sort: "-created_at",
    filter,
    expand: "reporter_id,reported_id"
  });

  return (
    <>
      <div className="row">
        <h1 style={{ margin: 0, fontFamily: "var(--font-title), ui-serif, serif", fontSize: 34 }}>Reports</h1>
        <Link className="pill" href="/admin">
          Admin home
        </Link>
      </div>

      <form method="GET" action="/admin/reports" className="card" style={{ marginTop: 12 }}>
        <div className="row" style={{ gap: 12 }}>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "baseline" }}>
            <label className="muted" htmlFor="status">
              Status
            </label>
            <select className="input" id="status" name="status" defaultValue={status}>
              <option value="">All</option>
              <option value="pending_admin">Pending admin</option>
              <option value="pending_ai">Pending AI</option>
              <option value="approved">Approved</option>
              <option value="dismissed">Dismissed</option>
            </select>
          </div>
          <button className="btn" type="submit">
            Filter
          </button>
        </div>
      </form>

      <div className="grid" style={{ marginTop: 12 }}>
        {reports.items.map((r) => {
          const reporter = r.expand?.reporter_id;
          const reported = r.expand?.reported_id;
          const resolved = r.status === "approved" || r.status === "dismissed";

          return (
            <div key={r.id} className="card">
              <div className="row">
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "baseline" }}>
                  <span style={{ fontWeight: 900 }}>{r.id}</span>
                  <span
                    className="pill"
                    style={
                      r.status === "approved"
                        ? { borderColor: "rgba(89,255,168,0.25)", color: "var(--good)" }
                        : r.status === "dismissed"
                          ? { opacity: 0.5 }
                          : r.status === "pending_admin"
                            ? { borderColor: "rgba(255,92,124,0.35)", color: "var(--bad)" }
                            : {}
                    }
                  >
                    {r.status}
                  </span>
                  {r.admin_decision ? <span className="pill">{r.admin_decision}</span> : null}
                </div>
                <div className="muted">{formatDate(r.created_at ?? "")}</div>
              </div>

              <div className="muted" style={{ marginTop: 8 }}>
                {memberLabel(reporter)} reported {memberLabel(reported)}
              </div>

              <div style={{ marginTop: 10, whiteSpace: "pre-wrap" }}>{r.description}</div>

              {r.evidence_photos && r.evidence_photos.length > 0 ? (
                <div style={{ marginTop: 10, display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {r.evidence_photos.map((photo, i) => (
                    <a
                      key={i}
                      href={pbFileUrl(r.collectionId, r.id, photo)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="pill"
                    >
                      Photo {i + 1}
                    </a>
                  ))}
                </div>
              ) : null}

              {r.ai_severity != null || r.ai_summary ? (
                <div
                  style={{
                    marginTop: 12,
                    borderTop: "1px solid var(--line)",
                    paddingTop: 10
                  }}
                >
                  <div className="muted" style={{ fontWeight: 800 }}>AI Assessment</div>
                  <div style={{ marginTop: 6, display: "flex", gap: 10, flexWrap: "wrap", alignItems: "baseline" }}>
                    {r.ai_severity != null ? (
                      <span className="pill" style={{ color: severityColor(r.ai_severity) }}>
                        Severity: {r.ai_severity}/10
                      </span>
                    ) : null}
                    {r.ai_recommendation ? (
                      <span
                        className="pill"
                        style={
                          r.ai_recommendation === "ban"
                            ? { borderColor: "rgba(255,92,124,0.35)", color: "var(--bad)" }
                            : r.ai_recommendation === "warn"
                              ? { color: "var(--accent)" }
                              : {}
                        }
                      >
                        Recommends: {r.ai_recommendation}
                      </span>
                    ) : null}
                  </div>
                  {r.ai_summary ? (
                    <div style={{ marginTop: 6, whiteSpace: "pre-wrap" }}>{r.ai_summary}</div>
                  ) : null}
                  {r.ai_reasoning ? (
                    <div className="muted" style={{ marginTop: 6, whiteSpace: "pre-wrap" }}>
                      {r.ai_reasoning}
                    </div>
                  ) : null}
                </div>
              ) : null}

              {resolved && r.resolved_at ? (
                <div className="muted" style={{ marginTop: 10 }}>
                  Resolved {formatDate(r.resolved_at)}
                </div>
              ) : null}

              {!resolved ? (
                <div
                  style={{
                    marginTop: 12,
                    borderTop: "1px solid var(--line)",
                    paddingTop: 10,
                    display: "flex",
                    gap: 10,
                    flexWrap: "wrap"
                  }}
                >
                  <form action={resolveReportAction}>
                    <input type="hidden" name="id" value={r.id} />
                    <input type="hidden" name="action" value="confirm_scammer" />
                    <input type="hidden" name="reported_member_id" value={reported?.id ?? ""} />
                    <button className="btn" type="submit" style={{ borderColor: "rgba(255,92,124,0.35)" }}>
                      Confirm scammer
                    </button>
                  </form>
                  <form action={resolveReportAction}>
                    <input type="hidden" name="id" value={r.id} />
                    <input type="hidden" name="action" value="warn" />
                    <input type="hidden" name="reported_member_id" value="" />
                    <button className="btn" type="submit">
                      Warn
                    </button>
                  </form>
                  <form action={resolveReportAction}>
                    <input type="hidden" name="id" value={r.id} />
                    <input type="hidden" name="action" value="dismiss" />
                    <input type="hidden" name="reported_member_id" value="" />
                    <button className="btn" type="submit">
                      Dismiss
                    </button>
                  </form>
                </div>
              ) : null}
            </div>
          );
        })}
      </div>

      <div style={{ display: "flex", gap: 10, justifyContent: "space-between", marginTop: 14, flexWrap: "wrap" }}>
        <div className="muted">
          Page {reports.page} of {reports.totalPages} (total {reports.totalItems})
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          {reports.page > 1 ? (
            <Link
              className="pill"
              href={`/admin/reports?page=${reports.page - 1}${status ? `&status=${encodeURIComponent(status)}` : ""}`}
            >
              Prev
            </Link>
          ) : null}
          {reports.page < reports.totalPages ? (
            <Link
              className="pill"
              href={`/admin/reports?page=${reports.page + 1}${status ? `&status=${encodeURIComponent(status)}` : ""}`}
            >
              Next
            </Link>
          ) : null}
        </div>
      </div>
    </>
  );
}
