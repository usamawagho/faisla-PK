import { AppointmentsPage } from "@/features/appointments/appointments-page";

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { lawyer_id } = await searchParams;
  return <AppointmentsPage defaultLawyerId={typeof lawyer_id === "string" ? lawyer_id : ""} />;
}
