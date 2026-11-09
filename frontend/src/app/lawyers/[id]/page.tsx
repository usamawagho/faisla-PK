import LawyerDetail from "@/features/lawyers/lawyer-detail";

export default async function LawyerPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <LawyerDetail id={id} />;
}
