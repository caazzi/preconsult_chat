import type { MouseEvent } from "react";

/**
 * Address-bar handling for the single-route SPA.
 *
 * The wizard has exactly one route (`/`); the backend serves the legal pages
 * and the crawler documents, so the client never renders a second path. That
 * made a full router dependency (react-router-dom + @remix-run/router) heavy
 * for what is one redirect, so the two behaviours it provided live here.
 */

/** Rewrite a stale path (e.g. a `/next/...` bookmark) to the root, keeping the query. */
export function normalizePath(): void {
  if (window.location.pathname !== "/") {
    window.history.replaceState({}, "", `/${window.location.search}`);
  }
}

/**
 * Home link handler. A plain anchor would reload the document and drop the
 * in-memory wizard draft (the intake is never persisted), so the click is
 * handled in place instead.
 */
export function handleHomeLink(event: MouseEvent<HTMLAnchorElement>): void {
  event.preventDefault();
  normalizePath();
}
