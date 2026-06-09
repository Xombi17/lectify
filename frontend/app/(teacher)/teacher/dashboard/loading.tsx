export default function TeacherDashboardLoading() {
  return (
    <div className="p-8 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="h-48 animate-pulse border border-border bg-muted/40" />
      ))}
    </div>
  );
}