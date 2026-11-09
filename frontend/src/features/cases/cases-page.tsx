"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { FormEvent, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { api, getApiError } from "@/lib/api";
import { useCurrentUser } from "@/features/shared/use-current-user";
import { formatDateTime, humanize } from "@/features/shared/format";
import type { CaseNote, CaseStatusEvent, LegalCase } from "@/types/workflows";

const priorities = ["low", "medium", "high", "urgent"] as const;
const caseStatuses = ["open", "in_progress", "waiting_client", "on_hold", "closed"] as const;
const allowedNextStatus: Record<LegalCase["status"], LegalCase["status"][]> = {
  open: ["in_progress", "waiting_client", "on_hold", "closed"],
  in_progress: ["waiting_client", "on_hold", "closed"],
  waiting_client: ["in_progress", "on_hold", "closed"],
  on_hold: ["in_progress", "waiting_client", "closed"],
  closed: [],
};

export function CasesPage() {
  const currentUser = useCurrentUser();
  const queryClient = useQueryClient();
  const user = currentUser.data;
  const [formError, setFormError] = useState("");
  const [statusFilter, setStatusFilter] = useState<LegalCase["status"] | "all">("all");
  const createForm = useRef<HTMLFormElement>(null);
  const cases = useQuery({
    queryKey: ["cases", user?.role],
    enabled: Boolean(user),
    queryFn: async () => (await api.get<LegalCase[]>(user?.role === "admin" ? "/cases" : "/cases/my")).data,
  });
  const createCase = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => api.post("/cases", payload),
    onSuccess: () => {
      setFormError("");
      createForm.current?.reset();
      void queryClient.invalidateQueries({ queryKey: ["cases"] });
    },
    onError: (error) => setFormError(getApiError(error, "Could not create the case.")),
  });
  const visibleCases = cases.data?.filter((item) => statusFilter === "all" || item.status === statusFilter);
  if (currentUser.isPending || !user) return <div className="page-shell"><div className="loading-state">Loading cases...</div></div>;
  return (
    <div className="page-shell">
      <div className="eyebrow">{user.role} workspace</div>
      <h1 className="page-title">Cases</h1>
      <p className="page-intro">Case records, updates, and documents shared with the assigned parties.</p>
      {user.role === "lawyer" && <form ref={createForm} className="workflow-form" onSubmit={(event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        createCase.mutate({
          client_id: Number(form.get("client_id")),
          title: form.get("title"),
          description: form.get("description"),
          case_type: form.get("case_type"),
          priority: form.get("priority"),
        });
      }}>
        <h2>Create a case</h2>
        <div className="workflow-form-grid">
          <label className="field">Client account ID<input type="number" min="1" name="client_id" required /></label>
          <label className="field">Case title<input name="title" maxLength={200} required /></label>
          <label className="field">Case type<input name="case_type" maxLength={100} required /></label>
          <label className="field">Priority<select name="priority" defaultValue="medium">{priorities.map((value) => <option value={value} key={value}>{humanize(value)}</option>)}</select></label>
        </div>
        <label className="field">Description<textarea name="description" rows={3} maxLength={10000} required /></label>
        {formError && <p className="form-error" role="alert">{formError}</p>}
        <button className="button button-small" disabled={createCase.isPending}>{createCase.isPending ? "Creating..." : "Create case"}</button>
      </form>}
      <div className="workflow-filters" aria-label="Filter cases">
        <button className={`filter-button ${statusFilter === "all" ? "filter-active" : ""}`} onClick={() => setStatusFilter("all")} type="button">All</button>
        {caseStatuses.map((status) => <button className={`filter-button ${statusFilter === status ? "filter-active" : ""}`} key={status} onClick={() => setStatusFilter(status)} type="button">{humanize(status)}</button>)}
      </div>
      {cases.isPending ? <div className="loading-state">Loading cases...</div> : cases.isError ? (
        <div className="error-state" role="alert">Cases could not be loaded. Please try again.</div>
      ) : (
        <div className="workflow-list">
          {visibleCases?.length ? visibleCases.map((legalCase) => (
            <Link className="workflow-card workflow-link" href={`/dashboard/cases/${legalCase.id}`} key={legalCase.id}>
              <div className="workflow-card-head">
                <div><h2>{legalCase.title}</h2><p>{humanize(legalCase.case_type)} · Updated {formatDateTime(legalCase.updated_at)}</p></div>
                <span className={`status-badge status-${legalCase.status}`}>{humanize(legalCase.status)}</span>
              </div>
              <p>{legalCase.description}</p>
              <p className="field-help">Client #{legalCase.client_id} · Lawyer #{legalCase.lawyer_id} · {humanize(legalCase.priority)} priority</p>
            </Link>
          )) : <div className="empty-state">{statusFilter === "all" ? "No cases are linked to your account yet." : `No ${humanize(statusFilter).toLowerCase()} cases.`}</div>}
        </div>
      )}
    </div>
  );
}

export function CaseDetailPage() {
  const params = useParams<{ id: string }>();
  const caseId = params.id;
  const currentUser = useCurrentUser();
  const queryClient = useQueryClient();
  const user = currentUser.data;
  const [error, setError] = useState("");
  const legalCase = useQuery({
    queryKey: ["case", caseId],
    enabled: Boolean(user && caseId),
    queryFn: async () => (await api.get<LegalCase>(`/cases/${caseId}`)).data,
  });
  const notes = useQuery({
    queryKey: ["case-notes", caseId],
    enabled: Boolean(legalCase.data),
    queryFn: async () => (await api.get<CaseNote[]>(`/cases/${caseId}/notes`)).data,
  });
  const history = useQuery({
    queryKey: ["case-history", caseId],
    enabled: Boolean(legalCase.data),
    queryFn: async () => (await api.get<CaseStatusEvent[]>(`/cases/${caseId}/status-history`)).data,
  });
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["case", caseId] });
    void queryClient.invalidateQueries({ queryKey: ["case-notes", caseId] });
    void queryClient.invalidateQueries({ queryKey: ["case-history", caseId] });
    void queryClient.invalidateQueries({ queryKey: ["cases"] });
  };
  const setStatus = useMutation({
    mutationFn: async (status: string) => api.put(`/cases/${caseId}/status`, { status }),
    onSuccess: () => { setError(""); refresh(); },
    onError: (cause) => setError(getApiError(cause, "Could not update case status.")),
  });
  const addNote = useMutation({
    mutationFn: async (note: string) => api.post(`/cases/${caseId}/notes`, { note }),
    onSuccess: () => { setError(""); setNoteText(""); refresh(); },
    onError: (cause) => setError(getApiError(cause, "Could not add the note.")),
  });
  const [noteText, setNoteText] = useState("");
  if (currentUser.isPending || !user || legalCase.isPending) return <div className="page-shell"><div className="loading-state">Loading case...</div></div>;
  if (legalCase.isError || !legalCase.data) return <div className="page-shell"><div className="error-state" role="alert">This case could not be loaded or you may not have access.</div></div>;
  const item = legalCase.data;
  const canEdit = user.role === "lawyer" && user.id === item.lawyer_id;
  return (
    <div className="page-shell">
      <Link className="text-link" href="/dashboard/cases">← All cases</Link>
      <div className="workflow-card case-detail-card">
        <div className="workflow-card-head"><div><div className="eyebrow">{humanize(item.case_type)}</div><h1>{item.title}</h1></div><span className={`status-badge status-${item.status}`}>{humanize(item.status)}</span></div>
        <p>{item.description}</p>
        <div className="case-meta"><span>Client #{item.client_id}</span><span>Lawyer #{item.lawyer_id}</span><span>{humanize(item.priority)} priority</span></div>
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      {canEdit && item.status !== "closed" && <section className="workflow-form">
        <h2>Update status</h2>
        <div className="status-actions">{allowedNextStatus[item.status].map((status) => (
          <button className="button button-small button-outline" key={status} disabled={setStatus.isPending} onClick={() => setStatus.mutate(status)}>{humanize(status)}</button>
        ))}</div>
      </section>}
      <section className="workflow-form">
        <h2>Status timeline</h2>
        {history.isError ? <p className="form-error">Status history could not be loaded.</p> : history.isPending ? <p>Loading status history...</p> : (
          <ol className="timeline">{history.data?.map((event) => (
            <li key={event.id}><span className="timeline-dot" /><div><strong>{event.previous_status ? `${humanize(event.previous_status)} → ${humanize(event.new_status)}` : `Case created · ${humanize(event.new_status)}`}</strong><p>Changed by user #{event.changed_by_id} · {formatDateTime(event.created_at)}</p></div></li>
          ))}</ol>
        )}
      </section>
      <section className="workflow-form">
        <h2>Case notes</h2>
        {canEdit && <NoteForm value={noteText} onChange={setNoteText} pending={addNote.isPending} onSubmit={(note) => addNote.mutate(note)} />}
        {notes.isError ? <p className="form-error">Notes could not be loaded.</p> : notes.isPending ? <p>Loading notes...</p> : notes.data?.length ? (
          <div className="workflow-list">{notes.data.map((note) => <article className="note-entry" key={note.id}><p>{note.note}</p><small>User #{note.author_id} · {formatDateTime(note.created_at)}</small></article>)}</div>
        ) : <p className="field-help">No notes have been added.</p>}
      </section>
      <CaseDocuments caseId={caseId} userId={user.id} userRole={user.role} />
    </div>
  );
}

function NoteForm({ value, onChange, pending, onSubmit }: { value: string; onChange: (value: string) => void; pending: boolean; onSubmit: (note: string) => void }) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (value.trim()) onSubmit(value.trim());
  }
  return <form className="note-form" onSubmit={submit}><label className="field">Add a note<textarea value={value} onChange={(event) => onChange(event.target.value)} maxLength={10000} rows={3} required /></label><button className="button button-small" disabled={pending}>{pending ? "Adding..." : "Add note"}</button></form>;
}

function CaseDocuments({ caseId, userId, userRole }: { caseId: string; userId: number; userRole: string }) {
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const docs = useQuery({
    queryKey: ["case-documents", caseId],
    queryFn: async () => (await api.get<import("@/types/workflows").CaseDocument[]>(`/cases/${caseId}/documents`)).data,
  });
  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const data = new FormData(formElement);
    setError("");
    try {
      await api.post(`/cases/${caseId}/documents`, data);
      formElement.reset();
      void queryClient.invalidateQueries({ queryKey: ["case-documents", caseId] });
    } catch (cause) {
      setError(getApiError(cause, "Could not upload this document."));
    }
  }
  async function removeDocument(id: string) {
    setError("");
    try {
      await api.delete(`/documents/${id}`);
      void queryClient.invalidateQueries({ queryKey: ["case-documents", caseId] });
    } catch (cause) {
      setError(getApiError(cause, "Could not delete this document."));
    }
  }
  return <section className="workflow-form">
    <h2>Case documents</h2>
    <form className="document-upload" onSubmit={upload}>
      <label className="field">Choose file (PDF, DOC, DOCX, JPG, PNG)<input type="file" name="file" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png" required /></label>
      <label className="field">Category<select name="document_type" defaultValue="other">{["contract", "evidence", "court_order", "agreement", "id_document", "other"].map((kind) => <option value={kind} key={kind}>{humanize(kind)}</option>)}</select></label>
      <label className="field">Description<input name="description" maxLength={1000} /></label>
      <button className="button button-small">Upload</button>
    </form>
    {error && <p className="form-error" role="alert">{error}</p>}
    {docs.isError ? <p className="form-error">Documents could not be loaded.</p> : docs.isPending ? <p>Loading documents...</p> : (
      <div className="workflow-list">{docs.data?.length ? docs.data.map((document) => (
        <article className="document-row" key={document.id}>
          <div><a className="text-link" href={document.storage_url} target="_blank" rel="noreferrer">{document.original_file_name}</a><p>{humanize(document.document_type)} · {(document.file_size / 1024 / 1024).toFixed(2)} MB · {formatDateTime(document.uploaded_at)}</p>{document.description && <small>{document.description}</small>}</div>
          {(userRole === "admin" || userId === document.uploaded_by || userRole === "lawyer") && <button className="link-button" type="button" onClick={() => void removeDocument(document.id)}>Delete</button>}
        </article>
      )) : <p className="field-help">No documents uploaded yet.</p>}</div>
    )}
  </section>;
}
