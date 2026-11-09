"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { type FormEvent, useState } from "react";
import { api, getApiError } from "@/lib/api";
import type { Lawyer } from "@/types/api";

interface SearchFilters {
  city?: string;
  specialization?: string;
  min_years_experience?: number;
}

export default function LawyersPage() {
  const [city, setCity] = useState("");
  const [specialization, setSpecialization] = useState("");
  const [experience, setExperience] = useState("");
  const [filters, setFilters] = useState<SearchFilters>({});

  const lawyersQuery = useQuery({
    queryKey: ["lawyers", filters],
    queryFn: async () => {
      const { data } = await api.get<Lawyer[]>("/lawyers", {
        params: {
          ...filters,
          limit: 30,
        },
      });
      return data;
    },
  });

  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFilters({
      ...(city.trim() ? { city: city.trim() } : {}),
      ...(specialization.trim() ? { specialization: specialization.trim() } : {}),
      ...(experience ? { min_years_experience: Number(experience) } : {}),
    });
  }

  return (
    <div className="page-shell">
      <div className="eyebrow">Lawyer directory</div>
      <h1 className="page-title">Find your legal counsel.</h1>
      <p className="page-intro">
        Search active lawyers with approved profiles by location, practice area, and experience.
      </p>

      <form className="search-panel" onSubmit={search}>
        <div className="field">
          <label htmlFor="city">City</label>
          <input id="city" onChange={(event) => setCity(event.target.value)} placeholder="e.g. Karachi" value={city} />
        </div>
        <div className="field">
          <label htmlFor="specialization">Practice area</label>
          <input id="specialization" onChange={(event) => setSpecialization(event.target.value)} placeholder="e.g. Family law" value={specialization} />
        </div>
        <div className="field">
          <label htmlFor="experience">Experience</label>
          <select id="experience" onChange={(event) => setExperience(event.target.value)} value={experience}>
            <option value="">Any</option>
            <option value="3">3+ years</option>
            <option value="5">5+ years</option>
            <option value="10">10+ years</option>
          </select>
        </div>
        <button className="button" type="submit">Search</button>
      </form>

      {lawyersQuery.isPending ? (
        <div className="loading-state">Finding lawyer profiles...</div>
      ) : lawyersQuery.isError ? (
        <div className="error-state" role="alert">
          {getApiError(lawyersQuery.error, "Lawyers could not be loaded. Please try again.")}
        </div>
      ) : lawyersQuery.data.length === 0 ? (
        <div className="empty-state">No matching lawyer profiles yet. Try a different city or practice area.</div>
      ) : (
        <>
          <p className="results-meta">
            {lawyersQuery.data.length} lawyer{lawyersQuery.data.length === 1 ? "" : "s"} found
          </p>
          <div className="lawyer-grid">
            {lawyersQuery.data.map((lawyer) => (
              <article className="lawyer-card" key={lawyer.id}>
                <div className="lawyer-card-head">
                  <div className="avatar" aria-hidden="true">{lawyer.full_name.charAt(0).toUpperCase()}</div>
                  <div>
                    <h2>{lawyer.full_name}</h2>
                    <p>{lawyer.specialization ?? "General practice"} · {lawyer.city ?? "Pakistan"}</p>
                  </div>
                </div>
                <div className="lawyer-meta">
                  <span className="meta-chip">{lawyer.years_of_experience} years’ experience</span>
                  {lawyer.verified && <span className="verified-pill">✓ Verified</span>}
                </div>
                <div className="lawyer-card-bottom">
                  <span className="lawyer-fee">
                    {lawyer.consultation_fee == null
                      ? "Fee on request"
                      : `PKR ${Number(lawyer.consultation_fee).toLocaleString()}`}
                  </span>
                  <Link className="text-link" href={`/lawyers/${lawyer.id}`}>View profile →</Link>
                </div>
              </article>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
