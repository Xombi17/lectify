export default function LectureDetailLoading() {
  return (
    <div role="status" aria-busy="true" aria-label="Loading" className="grid gap-4 p-8">
      <span className="sk w-2/3" />
      <span className="sk w-full" />
      <span className="sk w-5/6" />
      <span className="sk w-1/2" />
    </div>
  );
}
