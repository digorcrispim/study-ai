import { notFound } from "next/navigation";
import StudyQuiz from "./StudyQuiz";

type Material = {
  id: string;
  title: string;
  type: "pdf" | "video";
  storage_path: string | null;
  created_at: string;
};

type StudyQuestionData = {
  id: string;
  material_id: string | null;
  question_text: string;
  options: Record<string, string>;
  topics: string[] | null;
  difficulty: string | null;
  explanation: string | null;
};

async function getMaterial(id: string): Promise<Material> {
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

async function getQuestions(
  id: string
): Promise<StudyQuestionData[]> {
  const response = await fetch(
    `http://127.0.0.1:8000/questions/material/${id}/study`,
    {
      cache: "no-store",
    }
  );

  if (!response.ok) {
    throw new Error("Não foi possível carregar as questões.");
  }

  return response.json();
}

export default async function StudyPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ topic?: string | string[] }>;
}) {
  const [{ id }, query] = await Promise.all([params, searchParams]);
  const topicParam = query.topic;
  const selectedTopic = Array.isArray(topicParam)
    ? topicParam[0]
    : topicParam;

  const [material, questions] = await Promise.all([
    getMaterial(id),
    getQuestions(id),
  ]);
  const filteredQuestions =
    selectedTopic === undefined
      ? questions
      : questions.filter((question) =>
          question.topics?.some(
            (questionTopic) => questionTopic === selectedTopic
          )
        );

  return (
    <main className="min-h-screen bg-zinc-50 p-8">
      <div className="mx-auto max-w-4xl">
        <header className="mb-8">
          <p className="text-sm font-medium text-zinc-500">
            Modo de estudo
          </p>

          <h1 className="mt-2 text-3xl font-bold text-zinc-900">
            {material.title}
          </h1>

          <p className="mt-2 text-zinc-600">
            {filteredQuestions.length === 1
              ? "1 questão disponível."
              : `${filteredQuestions.length} questões disponíveis.`}
          </p>
        </header>

        {filteredQuestions.length === 0 ? (
          <div className="rounded-xl border border-dashed border-zinc-300 bg-white p-8 text-center text-zinc-500">
            {selectedTopic === undefined
              ? "Ainda não existem questões para este material."
              : `Ainda não existem questões para o tópico "${selectedTopic}" neste material.`}
          </div>
        ) : (
          <StudyQuiz
            questions={filteredQuestions}
            materialId={id}
            {...(selectedTopic !== undefined
              ? { topic: selectedTopic }
              : {})}
          />
        )}
      </div>
    </main>
  );
}
