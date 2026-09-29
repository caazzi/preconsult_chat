import { apiFetch } from "./client";
import type { SessionInitPayload } from "../wizard/payload";

/** Create an ephemeral session; sets the HttpOnly session cookie. */
export async function initSession(
  payload: SessionInitPayload,
): Promise<string> {
  const resp = await apiFetch("/session/init", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  const data = (await resp.json()) as { session_id?: string };
  if (!data.session_id) throw new Error("session_id missing from response");
  return data.session_id;
}
