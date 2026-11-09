"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api, getApiError } from "@/lib/api";
import type { Lawyer } from "@/types/api";
import { useAuthStore } from "@/lib/auth-store";

export default function LawyerDetail({ id }: { id: string }) {
  const user = useAuthStore((state) => state.user);
  const lawyerQuery = useQuery({
    queryKey: ["lawyer", id],
    queryFn: async () => {
      const { data } = await api.get<Lawyer>(`/lawyers/${encodeURIComponent(id)}`);
      return data;
    },
  });

  if (lawyerQuery.isPending) {
    return <div className="page-shell"><div className="loading-state">Loading lawyer profile...</div></div>;
  }
  if (lawyerQuery.isError) {
    return (
      <div className="page-shell">
        <div className="error-state" role="alert">
          {getApiError(lawyerQuery.error, "This lawyer profile could not be loaded.")}
          <p><Link className="text-link" href="/lawyers">Back to lawyer search</Link></p>
        </div>
      </div>
    );
  }

  const lawyer = lawyerQuery.data;
  return (
    <div className="page-shell">
      <Link className="text-link" href="/lawyers">← Back to lawyer search</Link>
      <section className="detail-card">
        <div className="detail-head">
          <div className="avatar" aria-hidden="true">{lawyer.full_name.charAt(0).toUpperCase()}</div>
          <div>
            <h1>{lawyer.full_name}</h1>
            <p>{lawyer.specialization ?? "General practice"} · {lawyer.city ?? "Pakistan"}</p>
            {lawyer.verified && <span className="verified-pill">✓ Verified profile</span>}
          </div>
        </div>
        <div className="detail-info-grid">
          <div className="detail-info">
            <small>Experience</small>
            <strong>{lawyer.years_of_experience} years</strong>
          </div>
          <div className="detail-info">
            <small>Consultation fee</small>
            <strong>{lawyer.consultation_fee == null ? "Contact for details" : `PKR ${Number(lawyer.consultation_fee).toLocaleString()}`}</strong>
          </div>
          <div className="detail-info">
            <small>Languages</small>
            <strong>{lawyer.languages.length ? lawyer.languages.join(", ") : "Ask the lawyer"}</strong>
          </div>
        </div>
        {lawyer.office_address && (
          <div className="detail-info">
            <small>Office</small>
            <strong>{lawyer.office_address}</strong>
          </div>
        )}
        <div className="hero-actions">
          {user?.role === "client" ? (
            <Link className="button" href={`/dashboard/appointments?lawyer_id=${lawyer.user_id}`}>Request a consultation</Link>
          ) : (
            <Link className="button" href="/login">Sign in to request a consultation</Link>
          )}
        </div>
      </section>
    </div>
  );
}
