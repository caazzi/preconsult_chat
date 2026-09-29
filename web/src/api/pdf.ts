// Deterministic PDF report. POST /api/generate-pdf returns application/pdf with
// a Content-Disposition filename; there is no LLM call.

import { apiFetch } from "./client";

export type QAPair = { question: string; answer: string };

function filenameFrom(resp: Response): string {
  const disp = resp.headers.get("Content-Disposition") ?? "";
  const match = /filename="?([^";]+)"?/i.exec(disp);
  return match?.[1] ?? "PreConsult_Report.pdf";
}

/** Fetch the PDF and trigger a browser download of the returned bytes. */
export async function downloadPdf(
  sessionId: string,
  qaPairs: QAPair[],
): Promise<void> {
  const resp = await apiFetch("/generate-pdf", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, qa_pairs: qaPairs }),
  });
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filenameFrom(resp);
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
