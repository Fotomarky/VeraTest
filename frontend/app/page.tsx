async function fetchRuns() {
  try {
    const res = await fetch(
      (process.env.SIMAB_API_URL || "http://localhost:8000") + "/api/runs?limit=20",
      { cache: "no-store" }
    );
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export default async function Home() {
  const runs = await fetchRuns();

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">Pretests</h1>
      <p className="text-sm text-neutral-600 mb-6">
        Simulate audience response before sending paid traffic.
      </p>

      {runs.length === 0 ? (
        <div className="rounded-lg border border-neutral-200 bg-white p-8 text-center">
          <p className="text-neutral-600 mb-4">No runs yet.</p>
          <a
            href="/new"
            className="inline-block px-4 py-2 rounded-md bg-neutral-900 text-white text-sm"
          >
            Start your first pretest
          </a>
        </div>
      ) : (
        <div className="space-y-2">
          {runs.map((r: any) => {
            const winner = r.synthesis?.winner ?? "—";
            const trust = r.audit?.trust_level ?? "—";
            return (
              <a
                key={r.run_id}
                href={`/runs/${r.run_id}`}
                className="block rounded-lg border border-neutral-200 bg-white p-4 hover:border-neutral-400 transition"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">{r.goal}</div>
                    <div className="text-xs text-neutral-500 mt-1 font-mono">{r.run_id}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-medium">
                      {r.status === "complete" ? (
                        <span className="text-emerald-700">winner: {winner}</span>
                      ) : (
                        <span className="text-amber-600">{r.status}</span>
                      )}
                    </div>
                    <div className="text-xs text-neutral-500">trust: {trust}</div>
                  </div>
                </div>
              </a>
            );
          })}
        </div>
      )}
    </div>
  );
}
