"use client";

import { type FormEvent, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

type AccountRole = "client" | "lawyer";
type RegistrationStep = 1 | 2 | 3;

const steps = [
  { title: "Account details", description: "Tell us how to reach you." },
  { title: "Your profile", description: "Add the details for your account." },
  { title: "Secure your account", description: "Choose a strong password." },
] as const;

export default function RegisterPage() {
  const router = useRouter();
  const formRef = useRef<HTMLFormElement>(null);
  const [role, setRole] = useState<AccountRole>("client");
  const [step, setStep] = useState<RegistrationStep>(1);
  const [form, setForm] = useState({
    email: "",
    password: "",
    confirm_password: "",
    phone: "",
    full_name: "",
    license_number: "",
    bar_council: "",
    bar_council_number: "",
    cnic: "",
    city: "Karachi",
    address: "",
    office_address: "",
    specialization: "",
    years_of_experience: "0",
  });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function setField(field: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function continueToNextStep() {
    if (!formRef.current?.reportValidity()) return;
    setError("");
    setStep((current) => Math.min(current + 1, 3) as RegistrationStep);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSuccess("");
    if (form.password !== form.confirm_password) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    const payload: Record<string, string> = {
      email: form.email.trim().toLowerCase(),
      password: form.password,
      phone: form.phone.trim(),
    };
    if (role === "lawyer") {
      Object.assign(payload, {
        full_name: form.full_name.trim(),
        license_number: form.license_number.trim(),
        bar_council: form.bar_council.trim(),
        bar_council_number: form.bar_council_number.trim(),
        cnic: form.cnic.trim(),
        city: form.city.trim(),
        office_address: form.office_address.trim(),
        specialization: form.specialization.trim(),
        years_of_experience: form.years_of_experience,
      });
    } else {
      Object.assign(payload, {
        full_name: form.full_name.trim(),
        city: form.city.trim(),
        address: form.address.trim(),
      });
      if (form.cnic.trim()) payload.cnic = form.cnic.trim();
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

  const passwordRequirements = [
    { label: "At least 8 characters", met: form.password.length >= 8 },
    { label: "An uppercase and a lowercase letter", met: /[A-Z]/.test(form.password) && /[a-z]/.test(form.password) },
    { label: "A number", met: /\d/.test(form.password) },
  ];

  return (
    <div className="auth-shell">
      <section aria-labelledby="registration-title" className="auth-card registration-card">
        <div className="eyebrow">Get started</div>
        <h1 id="registration-title">{step === 1 ? "Join Faisla" : steps[step - 1].title}</h1>
        <p className="auth-description">
          {step === 1
            ? "Choose your account type and enter your contact details."
            : steps[step - 1].description}
        </p>

        <div className="registration-progress">
          <ol aria-label="Registration steps">
            {steps.map((item, index) => {
              const stepNumber = index + 1;
              return (
                <li
                  aria-current={stepNumber === step ? "step" : undefined}
                  className={stepNumber <= step ? "progress-step is-complete" : "progress-step"}
                  key={item.title}
                >
                  <span className="progress-marker">{stepNumber < step ? "✓" : stepNumber}</span>
                  <span className="progress-label">{item.title}</span>
                </li>
              );
            })}
          </ol>
          <p>Step {step} of {steps.length}</p>
        </div>

        <form className="form-stack registration-form" onSubmit={submit} ref={formRef}>
          {step === 1 && (
            <>
              <fieldset className="account-type-field">
                <legend>Choose your account type</legend>
                <div className="account-type-options">
                  <button
                    aria-pressed={role === "client"}
                    className={role === "client" ? "account-type-option is-selected" : "account-type-option"}
                    onClick={() => setRole("client")}
                    type="button"
                  >
                    <span aria-hidden="true">◉</span>
                    <span>Client</span>
                  </button>
                  <button
                    aria-pressed={role === "lawyer"}
                    className={role === "lawyer" ? "account-type-option is-selected" : "account-type-option"}
                    onClick={() => setRole("lawyer")}
                    type="button"
                  >
                    <span aria-hidden="true">⚖</span>
                    <span>Lawyer</span>
                  </button>
                </div>
              </fieldset>
              <div className="field">
                <label htmlFor="full_name">Full name</label>
                <input
                  autoComplete="name"
                  autoFocus
                  id="full_name"
                  maxLength={200}
                  onChange={(event) => setField("full_name", event.target.value)}
                  required
                  value={form.full_name}
                />
              </div>
              <div className="field">
                <label htmlFor="email">Email address</label>
                <input
                  autoComplete="email"
                  id="email"
                  onChange={(event) => setField("email", event.target.value)}
                  required
                  type="email"
                  value={form.email}
                />
              </div>
              <div className="field">
                <label htmlFor="phone">Phone number</label>
                <input
                  autoComplete="tel"
                  id="phone"
                  maxLength={32}
                  onChange={(event) => setField("phone", event.target.value)}
                  required
                  type="tel"
                  value={form.phone}
                />
              </div>
            </>
          )}

          {step === 2 && role === "client" && (
            <>
              <div className="field">
                <label htmlFor="city">City</label>
                <input
                  autoComplete="address-level2"
                  autoFocus
                  id="city"
                  maxLength={100}
                  onChange={(event) => setField("city", event.target.value)}
                  required
                  value={form.city}
                />
              </div>
              <div className="field">
                <label htmlFor="address">Address</label>
                <textarea
                  autoComplete="street-address"
                  className="address-input"
                  id="address"
                  maxLength={500}
                  onChange={(event) => setField("address", event.target.value)}
                  placeholder="Street address, area, city"
                  required
                  rows={2}
                  value={form.address}
                />
              </div>
              <div className="field">
                <label htmlFor="cnic">CNIC <span className="field-help">(optional)</span></label>
                <input
                  autoComplete="off"
                  id="cnic"
                  maxLength={32}
                  onChange={(event) => setField("cnic", event.target.value)}
                  value={form.cnic}
                />
              </div>
            </>
          )}

          {step === 2 && role === "lawyer" && (
            <>
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="license_number">License number</label>
                  <input
                    autoFocus
                    id="license_number"
                    maxLength={100}
                    onChange={(event) => setField("license_number", event.target.value)}
                    required
                    value={form.license_number}
                  />
                </div>
                <div className="field">
                  <label htmlFor="bar_council">Bar council</label>
                  <input
                    id="bar_council"
                    maxLength={100}
                    onChange={(event) => setField("bar_council", event.target.value)}
                    required
                    value={form.bar_council}
                  />
                </div>
              </div>
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="bar_council_number">Bar council number</label>
                  <input
                    id="bar_council_number"
                    maxLength={100}
                    onChange={(event) => setField("bar_council_number", event.target.value)}
                    required
                    value={form.bar_council_number}
                  />
                </div>
                <div className="field">
                  <label htmlFor="cnic">CNIC</label>
                  <input
                    autoComplete="off"
                    id="cnic"
                    maxLength={32}
                    onChange={(event) => setField("cnic", event.target.value)}
                    required
                    value={form.cnic}
                  />
                </div>
              </div>
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="city">City</label>
                  <input
                    autoComplete="address-level2"
                    id="city"
                    maxLength={100}
                    onChange={(event) => setField("city", event.target.value)}
                    required
                    value={form.city}
                  />
                </div>
                <div className="field">
                  <label htmlFor="specialization">Specialization</label>
                  <input
                    id="specialization"
                    maxLength={200}
                    onChange={(event) => setField("specialization", event.target.value)}
                    required
                    value={form.specialization}
                  />
                </div>
              </div>
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="years_of_experience">Years of experience</label>
                  <input
                    id="years_of_experience"
                    max={80}
                    min={0}
                    onChange={(event) => setField("years_of_experience", event.target.value)}
                    required
                    type="number"
                    value={form.years_of_experience}
                  />
                </div>
                <div className="field">
                  <label htmlFor="office_address">Office address</label>
                  <input
                    autoComplete="street-address"
                    id="office_address"
                    maxLength={500}
                    onChange={(event) => setField("office_address", event.target.value)}
                    required
                    value={form.office_address}
                  />
                </div>
              </div>
            </>
          )}

          {step === 3 && (
            <>
              <div className="field">
                <label htmlFor="password">Password</label>
                <input
                  autoComplete="new-password"
                  autoFocus
                  id="password"
                  maxLength={128}
                  minLength={8}
                  onChange={(event) => setField("password", event.target.value)}
                  pattern="(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9]).{8,}"
                  required
                  title="Use at least 8 characters, including uppercase, lowercase, and a number."
                  type="password"
                  value={form.password}
                />
                <ul aria-label="Password requirements" className="password-requirements">
                  {passwordRequirements.map((requirement) => (
                    <li className={requirement.met ? "requirement-met" : ""} key={requirement.label}>
                      <span aria-hidden="true">{requirement.met ? "✓" : "○"}</span>
                      {requirement.label}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="field">
                <label htmlFor="confirm_password">Confirm password</label>
                <input
                  autoComplete="new-password"
                  id="confirm_password"
                  maxLength={128}
                  minLength={8}
                  onChange={(event) => setField("confirm_password", event.target.value)}
                  required
                  type="password"
                  value={form.confirm_password}
                />
                {form.confirm_password && form.password !== form.confirm_password && (
                  <span className="field-error" role="status">Passwords do not match yet.</span>
                )}
              </div>
            </>
          )}

          {error && <div className="form-error" role="alert">{error}</div>}
          {success && <div className="form-success" role="status">{success}</div>}

          <div className="registration-actions">
            {step > 1 && (
              <button
                className="button button-outline"
                onClick={() => {
                  setError("");
                  setStep((current) => Math.max(current - 1, 1) as RegistrationStep);
                }}
                type="button"
              >
                Back
              </button>
            )}
            {step < 3 ? (
              <button className="button auth-submit" onClick={continueToNextStep} type="button">
                Continue
                <span aria-hidden="true">→</span>
              </button>
            ) : (
              <button className="button auth-submit" disabled={submitting} type="submit">
                {submitting
                  ? "Creating account..."
                  : role === "lawyer"
                    ? "Submit lawyer application"
                    : "Create client account"}
              </button>
            )}
          </div>
        </form>

        <p className="auth-switch">Already registered? <Link href="/login">Sign in</Link></p>
      </section>
    </div>
  );
}
