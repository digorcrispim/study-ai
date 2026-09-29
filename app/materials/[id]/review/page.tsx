import { notFound } from "next/navigation";
import ReviewQuiz from "./ReviewQuiz";

type Material = {
  id: string;
  title: string;
};

async function getMaterial(
  id: string
): Promise<Material> {
  const response = await fetch(
    `http://127.0.0.1:8000/materials/${id}`,
    {
      cache: "no-store",
    }
  );

  if (!response.ok) {
    notFound();
  }

  return response.json();
}

export default async function ReviewPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const material = await getMaterial(id);

  return (
    <main className="min-h-screen bg-zinc-50 p-8">
      <div className="mx-auto max-w-4xl">
        <header className="mb-8">
          <p className="text-sm font-medium text-zinc-500">
            Modo de revisão
          </p>

          <h1 className="mt-2 text-3xl font-bold text-zinc-900">
            {material.title}
          </h1>

          <p className="mt-2 text-zinc-600">
            Revise as questões que estão vencidas.
          </p>
        </header>

        <ReviewQuiz materialId={id} />
      </div>
    </main>
  );
}
