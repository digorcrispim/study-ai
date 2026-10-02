"use client";

import { useState } from "react";
import { getUserId } from "@/lib/user";

type StudyQuestion = {
  id: string;
  question_text: string;
  options: Record<string, string>;
  difficulty: string | null;
};

export default function StudyQuestion({
  question,
}: {
  question: StudyQuestion;
}) {
  const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null);
  const [result, setResult] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);

  async function submitAnswer() {
    if (selectedAnswer === null || loading) return;

    setLoading(true);

    try {
      const response = await fetch(
        `/api/questions/${question.id}/answer`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            user_id: getUserId(),
            selected_answer: selectedAnswer,
          }),
        }
      );

      if (!response.ok) {
        throw new Error("Não foi possível registrar a resposta.");
      }

      const data = await response.json();
      setResult(data.is_correct);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  }

  return (
    <article className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
      <p className="text-sm font-medium text-zinc-500">Questão</p>

      <h2 className="mt-2 text-xl font-semibold text-zinc-900">
        {question.question_text}
      </h2>

      <div className="mt-5 space-y-3">
        {Object.entries(question.options).map(([key, option]) => {
          const optionNumber = Number(key);
          const selected = selectedAnswer === optionNumber;

          return (
            <button
              key={key}
              type="button"
              onClick={() => setSelectedAnswer(optionNumber)}
              className={`block w-full rounded-lg border p-4 text-left ${
                selected
                  ? "border-zinc-900 bg-zinc-100"
                  : "border-zinc-200 hover:bg-zinc-50"
              }`}
            >
              <span className="font-semibold">{key}.</span>{" "}
              {option}
            </button>
          );
        })}
      </div>

      <button
        type="button"
        onClick={submitAnswer}
        disabled={selectedAnswer === null || loading}
        className="mt-5 rounded-lg bg-zinc-900 px-5 py-3 font-medium text-white disabled:opacity-50"
      >
        {loading ? "Enviando..." : "Responder"}
      </button>

      {result !== null && (
        <div className="mt-5 rounded-lg border p-4">
          {result ? "✅ Resposta correta!" : "❌ Resposta incorreta."}
        </div>
      )}

      {question.difficulty && (
        <p className="mt-4 text-sm text-zinc-500">
          Dificuldade: {question.difficulty}
        </p>
      )}
    </article>
  );
}
