export function Placeholder({ title, milestone, todo }: { title: string; milestone: string; todo: string }) {
  return (
    <>
      <h1>{title}</h1>
      <section className="card">
        <p>
          Trang này làm ở <strong>{milestone}</strong>, sau khi nhóm chốt topic và có nguồn thật.
        </p>
        <p className="muted">{todo}</p>
      </section>
    </>
  );
}
