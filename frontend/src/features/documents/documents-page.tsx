"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { FormEvent, useState } from "react";
import { api, getApiError } from "@/lib/api";
import { useCurrentUser } from "@/features/shared/use-current-user";
import { formatDateTime, humanize } from "@/features/shared/format";
import type { CaseDocument, LegalCase } from "@/types/workflows";

export function DocumentsPage() {
  const currentUser = useCurrentUser();
  const user = currentUser.data;
  const [selectedCase, setSelectedCase] = useState("");
  const [error, setError] = useState("");
  const queryClient = useQueryClient();
  const cases = useQuery({
    queryKey: ["cases", user?.role],
    enabled: Boolean(user && user.role !== "admin"),
    queryFn: async () => (await api.get<LegalCase[]>(user?.role === "admin" ? "/cases" : "/cases/my")).data,
  });
  const documents = useQuery({
    queryKey: ["case-documents", selectedCase],
    enabled: Boolean(selectedCase),
    queryFn: async () => (await api.get<CaseDocument[]>(`/cases/${selectedCase}/documents`)).data,
  });
  if (currentUser.isPending || !user) return <div className="page-shell"><div className="loading-state">Loading documents...</div></div>;
  return (
    <div className="page-shell">
      <div className="eyebrow">{user.role} workspace</div>
      <h1 className="page-title">Documents</h1>
      <p className="page-intro">Access secure documents shared on your cases. Downloads use short-lived signed links.</p>
      {user.role === "admin" ? <div className="empty-state">Documents are available from an individual case, not from the admin workspace.</div> : (
        <>
          <label className="field case-picker">Select a case<select value={selectedCase} onChange={(event) => setSelectedCase(event.target.value)}><option value="">Choose a case</option>{cases.data?.map((item) => <option value={item.id} key={item.id}>{item.title}</option>)}</select></label>
          {cases.isError && <p className="form-error" role="alert">Your cases could not be loaded.</p>}
          {selectedCase && <>
            <UploadDocument caseId={selectedCase} onUploaded={() => void queryClient.invalidateQueries({ queryKey: ["case-documents", selectedCase] })} onError={setError} />
            {error && <p className="form-error" role="alert">{error}</p>}
            {documents.isPending ? <div className="loading-state">Loading case documents...</div> : documents.isError ? <div className="error-state">Documents could not be loaded for this case.</div> : (
              <div className="workflow-list">{documents.data?.length ? documents.data.map((document) => (
                <article className="document-row" key={document.id}>
                  <div><a className="text-link" href={document.storage_url} target="_blank" rel="noreferrer">{document.original_file_name}</a><p>{humanize(document.document_type)} · {formatDateTime(document.uploaded_at)} · {(document.file_size / 1024 / 1024).toFixed(2)} MB</p>{document.description && <small>{document.description}</small>}</div>
                  <Link className="button button-small button-outline" href={`/dashboard/cases/${selectedCase}`}>Open case</Link>
                </article>
              )) : <div className="empty-state">No documents uploaded to this case yet.</div>}</div>
            )}
          </>}
        </>
      )}
    </div>
  );
}

function UploadDocument({ caseId, onUploaded, onError }: { caseId: string; onUploaded: () => void; onError: (message: string) => void }) {
  const [pending, setPending] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    setPending(true);
    onError("");
    try {
      await api.post(`/cases/${caseId}/documents`, new FormData(formElement));
      formElement.reset();
      onUploaded();
    } catch (error) {
      onError(getApiError(error, "Upload failed. Files must be an allowed type and no larger than 10 MB."));
    } finally {
      setPending(false);
    }
  }
  return <form className="workflow-form document-upload" onSubmit={submit}>
    <h2>Upload a document</h2>
    <label className="field">File (PDF, DOC, DOCX, JPG, PNG; up to 10 MB)<input type="file" name="file" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png" required /></label>
    <label className="field">Category<select name="document_type" defaultValue="other">{["contract", "evidence", "court_order", "agreement", "id_document", "other"].map((kind) => <option value={kind} key={kind}>{humanize(kind)}</option>)}</select></label>
    <label className="field">Description<input name="description" maxLength={1000} /></label>
    <button className="button button-small" disabled={pending}>{pending ? "Uploading..." : "Upload securely"}</button>
  </form>;
}
