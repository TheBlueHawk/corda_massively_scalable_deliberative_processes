type ErrorStateProps = {
  title: string;
  detail: string;
};

export function ErrorState({ title, detail }: ErrorStateProps) {
  return (
    <main className="shell">
      <section className="empty-state">
        <h1>{title}</h1>
        <p>{detail}</p>
      </section>
    </main>
  );
}
