"use client";

import { type FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

type AccountRole = "client" | "lawyer";

export default function RegisterPage() {
  const router = useRouter();
  const [role, setRole] = useState<AccountRole>("client");
  const [form, setForm] = useState({
    email: "",
    password: "",
    phone: "",
    full_name: "",
    license_number: "",
    bar_council: "",
    bar_council_number: "",
    cnic: "",
    city: "Karachi",
    specialization: "",
  });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function setField(field: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSuccess("");
    setSubmitting(true);
    const payload: Record<string, string> = {
      email: form.email.trim().toLowerCase(),
      password: form.password,
    };
    if (form.phone.trim()) payload.phone = form.phone.trim();
    if (role === "lawyer") {
      Object.assign(payload, {
        full_name: form.full_name.trim(),
        license_number: form.license_number.trim(),
        bar_council: form.bar_council.trim(),
        bar_council_number: form.bar_council_number.trim(),
        cnic: form.cnic.trim(),
        city: form.city.trim(),
      });
      if (form.specialization.trim()) payload.specialization = form.specialization.trim();
    }

    try {
      const response = await fetch(`/api/auth/register/${role}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as
          | { detail?: unknown }
          | null;
        const detail = body?.detail;
        throw new Error(
          typeof detail === "string"
            ? detail
            : Array.isArray(detail) && detail.length
              ? detail
                  .map((item) =>
                    typeof item === "object" &&
                    item !== null &&
                    "msg" in item &&
                    typeof item.msg === "string"
                      ? item.msg
                      : "",
                  )
                  .filter(Boolean)
                  .join(" ")
              : "Please check your details and try again.",
        );
      }
      setSuccess(
        role === "lawyer"
          ? "Your application is submitted. Sign in after registration; your profile will be reviewed."
          : "Your account is ready. Sign in to continue.",
      );
      window.setTimeout(() => router.push("/login"), 1200);
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Registration failed. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-shell">
      <section className="auth-card">
        <div className="eyebrow">Get started</div>
        <h1>Create your account</h1>
        <p>Choose how you will use Faisla PK. Lawyer profiles are reviewed before appearing in search.</p>
        <form className="form-stack" onSubmit={submit}>
          <div className="field">
            <label htmlFor="role">I am a</label>
            <select id="role" onChange={(event) => setRole(event.target.value as AccountRole)} value={role}>
              <option value="client">Client</option>
              <option value="lawyer">Lawyer</option>
            </select>
          </div>
          {role === "lawyer" && (
            <>
              <div className="field">
                <label htmlFor="full_name">Full name</label>
                <input autoComplete="name" id="full_name" maxLength={200} onChange={(event) => setField("full_name", event.target.value)} required value={form.full_name} />
              </div>
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="license_number">License number</label>
                  <input id="license_number" maxLength={100} onChange={(event) => setField("license_number", event.target.value)} required value={form.license_number} />
                </div>
                <div className="field">
                  <label htmlFor="bar_council">Bar council</label>
                  <input id="bar_council" maxLength={100} onChange={(event) => setField("bar_council", event.target.value)} required value={form.bar_council} />
                </div>
              </div>
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="bar_council_number">Bar council number</label>
                  <input id="bar_council_number" maxLength={100} onChange={(event) => setField("bar_council_number", event.target.value)} required value={form.bar_council_number} />
                </div>
                <div className="field">
                  <label htmlFor="cnic">CNIC</label>
                  <input autoComplete="off" id="cnic" maxLength={32} onChange={(event) => setField("cnic", event.target.value)} required value={form.cnic} />
                </div>
              </div>
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="city">City</label>
                  <input id="city" maxLength={100} onChange={(event) => setField("city", event.target.value)} required value={form.city} />
                </div>
                <div className="field">
                  <label htmlFor="specialization">Specialization</label>
                  <input id="specialization" maxLength={200} onChange={(event) => setField("specialization", event.target.value)} value={form.specialization} />
                </div>
              </div>
            </>
          )}
          <div className="field">
            <label htmlFor="email">Email address</label>
            <input autoComplete="email" id="email" onChange={(event) => setField("email", event.target.value)} required type="email" value={form.email} />
          </div>
          <div className="field">
            <label htmlFor="phone">Phone number <span className="field-help">(optional)</span></label>
            <input autoComplete="tel" id="phone" maxLength={32} onChange={(event) => setField("phone", event.target.value)} value={form.phone} />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input autoComplete="new-password" id="password" maxLength={128} minLength={8} onChange={(event) => setField("password", event.target.value)} required type="password" value={form.password} />
            <span className="field-help">At least 8 characters, including uppercase, lowercase, and a number.</span>
          </div>
          {error && <div className="form-error" role="alert">{error}</div>}
          {success && <div className="form-success" role="status">{success}</div>}
          <button className="button auth-submit" disabled={submitting} type="submit">
            {submitting ? "Creating account..." : role === "lawyer" ? "Submit lawyer application" : "Create client account"}
          </button>
        </form>
        <p className="auth-switch">Already registered? <Link href="/login">Sign in</Link></p>
      </section>
    </div>
  );
}
