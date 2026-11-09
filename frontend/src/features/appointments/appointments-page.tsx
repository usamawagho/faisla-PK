"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { api, getApiError } from "@/lib/api";
import { useCurrentUser } from "@/features/shared/use-current-user";
import { currentPakistanDate, formatDate, formatTime, humanize } from "@/features/shared/format";
import type { Appointment, Availability } from "@/types/workflows";

const weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
type AppointmentFilter = "all" | "upcoming" | Appointment["status"];

export function AppointmentsPage({ defaultLawyerId = "" }: { defaultLawyerId?: string }) {
  const currentUser = useCurrentUser();
  const queryClient = useQueryClient();
  const user = currentUser.data;
  const [formError, setFormError] = useState("");
  const [notice, setNotice] = useState("");
  const [filter, setFilter] = useState<AppointmentFilter>("all");
  const appointments = useQuery({
    queryKey: ["appointments", user?.role],
    enabled: Boolean(user && user.role !== "admin"),
    queryFn: async () => {
      const { data } = await api.get<Appointment[]>(
        user?.role === "lawyer" ? "/appointments/lawyer" : "/appointments/my",
      );
      return data;
    },
  });
  const availability = useQuery({
    queryKey: ["my-availability"],
    enabled: user?.role === "lawyer",
    queryFn: async () => (await api.get<Availability[]>("/availability/me")).data,
  });
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["appointments"] });
    void queryClient.invalidateQueries({ queryKey: ["my-availability"] });
  };
  const statusMutation = useMutation({
    mutationFn: async ({ id, action }: { id: string; action: "approve" | "reject" | "complete" | "cancel" }) =>
      api.put(`/appointments/${id}/${action}`),
    onSuccess: (_, variables) => {
      setNotice({
        approve: "Appointment approved.",
        reject: "Appointment rejected.",
        complete: "Appointment marked complete.",
        cancel: "Appointment cancelled.",
      }[variables.action]);
      setFormError("");
      refresh();
    },
    onError: (error) => setFormError(getApiError(error, "Could not update this appointment.")),
  });
  const visibleAppointments = appointments.data?.filter((appointment) => {
    if (filter === "all") return true;
    if (filter === "upcoming") {
      const start = new Date(`${appointment.appointment_date}T${appointment.appointment_time}+05:00`);
      return start.getTime() >= Date.now() && ["pending", "approved"].includes(appointment.status);
    }
    return appointment.status === filter;
  });

  if (currentUser.isPending || !user) return <div className="page-shell"><div className="loading-state">Loading appointments...</div></div>;
  if (user.role === "admin") return <div className="page-shell"><h1 className="page-title">Appointments</h1><p className="page-intro">Appointment management is available to clients and lawyers.</p></div>;

  return (
    <div className="page-shell">
      <div className="eyebrow">{user.role} workspace</div>
      <h1 className="page-title">Appointments</h1>
      <p className="page-intro">
        {user.role === "client" ? "Request consultations and follow each booking." : "Review requests and manage your availability."}
      </p>
      {formError && <p className="form-error" role="alert">{formError}</p>}
      {notice && <p className="form-success" role="status">{notice}</p>}
      {appointments.isPending ? <div className="loading-state">Loading appointments...</div> : appointments.isError ? (
        <div className="error-state" role="alert">Appointments could not be loaded. Please try again.</div>
      ) : (
        <>
          {user.role === "client" && <AppointmentRequest defaultLawyerId={defaultLawyerId} onCreated={() => { refresh(); setNotice("Appointment request sent."); }} />}
          {user.role === "lawyer" && <AvailabilityManager availability={availability.data ?? []} onChanged={refresh} />}
          <div className="workflow-filters" aria-label="Filter appointments">
            {(["all", "upcoming", "pending", "approved", "rejected", "completed", "cancelled"] as const).map((value) => (
              <button className={`filter-button ${filter === value ? "filter-active" : ""}`} key={value} onClick={() => setFilter(value)} type="button">{humanize(value)}</button>
            ))}
          </div>
          <div className="workflow-list">
            {visibleAppointments?.length ? visibleAppointments.map((appointment) => (
              <article className="workflow-card" key={appointment.id}>
                <div className="workflow-card-head">
                  <div><h2>{user.role === "lawyer" ? `Client #${appointment.client_id}` : `Lawyer #${appointment.lawyer_id}`}</h2>
                    <p>{formatDate(appointment.appointment_date)} · {formatTime(appointment.appointment_time)}</p></div>
                  <span className={`status-badge status-${appointment.status}`}>{humanize(appointment.status)}</span>
                </div>
                <p>{humanize(appointment.consultation_type)} consultation</p>
                {appointment.notes && <p className="workflow-note">{appointment.notes}</p>}
                <div className="workflow-actions">
                  {user.role === "lawyer" && appointment.status === "pending" && <>
                    <button className="button button-small" disabled={statusMutation.isPending} onClick={() => statusMutation.mutate({ id: appointment.id, action: "approve" })}>Approve</button>
                    <button className="button button-small button-danger" disabled={statusMutation.isPending} onClick={() => statusMutation.mutate({ id: appointment.id, action: "reject" })}>Reject</button>
                  </>}
                  {user.role === "lawyer" && appointment.status === "approved" &&
                    <button className="button button-small" disabled={statusMutation.isPending} onClick={() => statusMutation.mutate({ id: appointment.id, action: "complete" })}>Mark complete</button>}
                  {user.role === "client" && appointment.status === "pending" &&
                    <button className="button button-small button-outline" disabled={statusMutation.isPending} onClick={() => statusMutation.mutate({ id: appointment.id, action: "cancel" })}>Cancel request</button>}
                </div>
              </article>
            )) : <div className="empty-state">{filter === "all" ? "No appointments yet." : `No ${humanize(filter).toLowerCase()} appointments.`}</div>}
          </div>
        </>
      )}
    </div>
  );
}

function AppointmentRequest({ defaultLawyerId, onCreated }: { defaultLawyerId: string; onCreated: () => void }) {
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setPending(true);
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const payload = {
      lawyer_id: Number(form.get("lawyer_id")),
      appointment_date: form.get("appointment_date"),
      appointment_time: form.get("appointment_time"),
      consultation_type: form.get("consultation_type"),
      notes: form.get("notes") || null,
    };
    try {
      await api.post("/appointments", payload);
      formElement.reset();
      onCreated();
    } catch (requestError) {
      setError(getApiError(requestError, "Could not request an appointment."));
    } finally {
      setPending(false);
    }
  }
  return (
    <form className="workflow-form" onSubmit={submit}>
      <h2>Request a consultation</h2>
      <div className="workflow-form-grid">
        <label className="field">Lawyer account ID<input name="lawyer_id" type="number" min="1" defaultValue={defaultLawyerId} required /></label>
        <label className="field">Date<input name="appointment_date" type="date" min={currentPakistanDate()} required /></label>
        <label className="field">Time (Pakistan time)<input name="appointment_time" type="time" required /></label>
        <label className="field">Consultation type<select name="consultation_type" defaultValue="online"><option value="online">Online</option><option value="in_person">In person</option></select></label>
      </div>
      <label className="field">Note (optional)<textarea name="notes" maxLength={2000} rows={3} /></label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="button button-small" disabled={pending}>{pending ? "Sending..." : "Request appointment"}</button>
    </form>
  );
}

function AvailabilityManager({ availability, onChanged }: { availability: Availability[]; onChanged: () => void }) {
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  async function addSlot(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setPending(true);
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
      await api.post("/availability", {
        day_of_week: Number(form.get("day_of_week")),
        start_time: form.get("start_time"),
        end_time: form.get("end_time"),
        is_active: true,
      });
      formElement.reset();
      onChanged();
    } catch (requestError) {
      setError(getApiError(requestError, "Could not add availability."));
    } finally {
      setPending(false);
    }
  }
  async function removeSlot(id: string) {
    setError("");
    try {
      await api.delete(`/availability/${id}`);
      onChanged();
    } catch (requestError) {
      setError(getApiError(requestError, "Could not remove this availability."));
    }
  }
  return (
    <section className="workflow-form">
      <h2>Availability</h2>
      <form className="workflow-form-grid availability-form" onSubmit={addSlot}>
        <label className="field">Day<select name="day_of_week">{weekdays.map((day, index) => <option value={index} key={day}>{day}</option>)}</select></label>
        <label className="field">Start<input name="start_time" type="time" required /></label>
        <label className="field">End<input name="end_time" type="time" required /></label>
        <button className="button button-small" disabled={pending}>{pending ? "Adding..." : "Add hours"}</button>
      </form>
      {error && <p className="form-error" role="alert">{error}</p>}
      <ul className="availability-list">{availability.map((slot) => (
        <li key={slot.id}><span>{weekdays[slot.day_of_week]} · {formatTime(slot.start_time)}–{formatTime(slot.end_time)}{slot.is_active ? "" : " · Inactive"}</span><div className="workflow-actions"><button className="link-button" type="button" onClick={() => void api.put(`/availability/${slot.id}`, { is_active: !slot.is_active }).then(onChanged).catch((requestError: unknown) => setError(getApiError(requestError, "Could not update this availability.")))}>{slot.is_active ? "Pause" : "Activate"}</button><button className="link-button" type="button" onClick={() => void removeSlot(slot.id)}>Remove</button></div></li>
      ))}</ul>
    </section>
  );
}
