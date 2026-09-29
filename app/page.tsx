import Link from "next/link";

type Material = {
  id: string;
  title: string;
  type: "pdf" | "video";
  storage_path: string | null;
  created_at: string;
};

async function getMaterials(): Promise<Material[]> {
  const response = await fetch("http://127.0.0.1:8000/materials", {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Não foi possível carregar os materiais.");
  }

  return response.json();
}

export default async function Home() {
  const materials = await getMaterials();

  return (
    <main className="min-h-screen bg-zinc-50 p-8">
      <div className="mx-auto max-w-4xl">
        <header className="mb-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-3xl font-bold text-zinc-900">
                Study AI
              </h1>

              <p className="mt-2 text-zinc-600">
                Sua plataforma de estudos inteligente.
              </p>
            </div>

            <Link
              href="/performance"
              className="rounded-lg border border-zinc-300 bg-white px-4 py-2 text-center font-medium text-zinc-900 hover:bg-zinc-50"
            >
              
Meu desempenho
            </Link>
            <Link
              href="/history"
              className="rounded-lg border border-zinc-300 bg-white px-4 py-2 text-center font-medium text-zinc-900 hover:bg-zinc-50"
            >
              Histórico
            </Link>
          </div>
        </header>

        <section>
          <h2 className="mb-4 text-xl font-semibold text-zinc-900">
            Materiais de estudo
          </h2>

          {materials.length === 0 ? (
            <div className="rounded-xl border border-dashed border-zinc-300 bg-white p-8 text-center text-zinc-500">
              Nenhum material cadastrado.
            </div>
          ) : (
            <div className="grid gap-4">
              {materials.map((material) => (
                <article
                  key={material.id}
                  className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm"
                >
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <h3 className="text-lg font-semibold text-zinc-900">
                        {material.title}
                      </h3>

                      <p className="mt-2 text-sm text-zinc-500">
                        Tipo: {material.type.toUpperCase()}
                      </p>
                    </div>

                    <div className="flex flex-col gap-2 sm:flex-row">
                      <Link
                        href={`/materials/${material.id}`}
                        className="rounded-lg bg-zinc-900 px-5 py-3 text-center font-medium text-white hover:bg-zinc-800"
                      >
                        Estudar
                      </Link>

                      <Link
                        href={`/materials/${material.id}/review`}
                        className="rounded-lg border border-zinc-300 px-5 py-3 text-center font-medium text-zinc-900 hover:bg-zinc-50"
                      >
                        Revisar
                      </Link>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
