"use client";

import { useState } from "react";
import { getUserId } from "@/lib/user";

type StudyQuestion = {
  id: string;
  question_text: string;
  options: Record<string, string>;
  difficulty: string | null;
};

type StudyQuizProps = {
  questions: StudyQuestion[];
};


export default function StudyQuiz({
  questions,
}: StudyQuizProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null);
  const [result, setResult] = useState<boolean | null>(null);
  const [correctAnswers, setCorrectAnswers] = useState(0);
  const [answered, setAnswered] = useState(false);
  const [loading, setLoading] = useState(false);

  const currentQuestion = questions[currentIndex];
  const finished = currentIndex >= questions.length;

  async function submitAnswer() {
    if (
      selectedAnswer === null ||
      loading ||
      answered
    ) {
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/questions/${currentQuestion.id}/answer`,
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
        throw new Error(
          "Não foi possível registrar a resposta."
        );
      }

      const data = await response.json();

      setResult(data.is_correct);
      setAnswered(true);

      if (data.is_correct) {
        setCorrectAnswers((value) => value + 1);
      }
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  }

  function nextQuestion() {
    setCurrentIndex((value) => value + 1);
    setSelectedAnswer(null);
    setResult(null);
    setAnswered(false);
  }

  if (finished) {
    const total = questions.length;
    const accuracy =
      total > 0 ? (correctAnswers / total) * 100 : 0;

    return (
      <section className="rounded-xl border border-zinc-200 bg-white p-8 shadow-sm">
        <p className="text-sm font-medium text-zinc-500">
          Sessão concluída
        </p>

        <h2 className="mt-2 text-3xl font-bold text-zinc-900">
          Muito bem!
        </h2>

        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          <div className="rounded-lg bg-zinc-50 p-4">
            <p className="text-sm text-zinc-500">
              Questões
            </p>
            <p className="mt-1 text-2xl font-bold">
              {total}
            </p>
          </div>

          <div className="rounded-lg bg-zinc-50 p-4">
            <p className="text-sm text-zinc-500">
              Acertos
            </p>
            <p className="mt-1 text-2xl font-bold">
              {correctAnswers}
            </p>
          </div>

          <div className="rounded-lg bg-zinc-50 p-4">
            <p className="text-sm text-zinc-500">
              Precisão
            </p>
            <p className="mt-1 text-2xl font-bold">
              {accuracy.toFixed(1)}%
            </p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-zinc-500">
          Questão {currentIndex + 1} de {questions.length}
        </p>

        <p className="text-sm text-zinc-500">
          Acertos: {correctAnswers}
        </p>
      </div>

      <h2 className="mt-4 text-xl font-semibold text-zinc-900">
        {currentQuestion.question_text}
      </h2>

      <div className="mt-6 space-y-3">
        {Object.entries(currentQuestion.options).map(
          ([key, option]) => {
            const optionNumber = Number(key);
            const selected =
              selectedAnswer === optionNumber;

            return (
              <button
                key={key}
                type="button"
                disabled={answered}
                onClick={() =>
                  setSelectedAnswer(optionNumber)
                }
                className={`block w-full rounded-lg border p-4 text-left transition ${
                  selected
                    ? "border-zinc-900 bg-zinc-100"
                    : "border-zinc-200 hover:bg-zinc-50"
                } ${
                  answered
                    ? "cursor-default"
                    : "cursor-pointer"
                }`}
              >
                <span className="font-semibold">
                  {key}.
                </span>{" "}
                {option}
              </button>
            );
          }
        )}
      </div>

      {!answered && (
        <button
          type="button"
          onClick={submitAnswer}
          disabled={
            selectedAnswer === null || loading
          }
          className="mt-6 rounded-lg bg-zinc-900 px-5 py-3 font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Enviando..." : "Responder"}
        </button>
      )}

      {result !== null && (
        <div className="mt-6 rounded-lg border p-4">
          {result ? (
            <p className="font-medium">
              ✅ Resposta correta!
            </p>
          ) : (
            <p className="font-medium">
              ❌ Resposta incorreta.
            </p>
          )}
        </div>
      )}

      {answered && (
        <button
          type="button"
          onClick={nextQuestion}
          className="mt-4 rounded-lg border border-zinc-300 px-5 py-3 font-medium text-zinc-900 hover:bg-zinc-50"
        >
          {currentIndex === questions.length - 1
            ? "Ver resultado"
            : "Próxima questão"}
        </button>
      )}

      {currentQuestion.difficulty && (
        <p className="mt-4 text-sm text-zinc-500">
          Dificuldade: {currentQuestion.difficulty}
        </p>
      )}
    </section>
  );
}
