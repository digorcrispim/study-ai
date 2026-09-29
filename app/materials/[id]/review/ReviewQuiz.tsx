"use client";

import { useEffect, useState } from "react";
import { getUserId } from "@/lib/user";

type ReviewQuestion = {
  id: string;
  question_text: string;
  options: Record<string, string>;
  topics: string[] | null;
  difficulty: string | null;
  explanation: string | null;
};

type ReviewQuizProps = {
  materialId: string;
};

export default function ReviewQuiz({
  materialId,
}: ReviewQuizProps) {
  const [questions, setQuestions] = useState<ReviewQuestion[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedAnswer, setSelectedAnswer] =
    useState<number | null>(null);
  const [result, setResult] = useState<boolean | null>(null);
  const [answered, setAnswered] = useState(false);
  const [correctAnswers, setCorrectAnswers] = useState(0);
  const [sessionAnsweredIds, setSessionAnsweredIds] =
    useState<string[]>([]);
  const [loadingQuestions, setLoadingQuestions] = useState(true);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function loadReviewQuestions() {
      try {
        const response = await fetch(
          `http://127.0.0.1:8000/questions/material/${materialId}/review/${getUserId()}`,
          {
            cache: "no-store",
          }
        );

        if (!response.ok) {
          throw new Error(
            "Não foi possível carregar as revisões."
          );
        }

        const data: ReviewQuestion[] =
          await response.json();

        setQuestions(data);
      } catch (error) {
        console.error(error);
      } finally {
        setLoadingQuestions(false);
      }
    }

    loadReviewQuestions();
  }, [materialId]);

  const currentQuestion = questions[currentIndex];

  async function submitAnswer() {
    if (
      selectedAnswer === null ||
      loading ||
      answered ||
      !currentQuestion
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
      setSessionAnsweredIds((ids) => [
        ...ids,
        currentQuestion.id,
      ]);

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

  if (loadingQuestions) {
    return (
      <section className="rounded-xl border border-zinc-200 bg-white p-8 text-center shadow-sm">
        <p className="text-sm text-zinc-500">
          Carregando revisões...
        </p>
      </section>
    );
  }

  if (questions.length === 0) {
    return (
      <section className="rounded-xl border border-dashed border-zinc-300 bg-white p-8 text-center shadow-sm">
        <p className="text-sm font-medium text-zinc-500">
          Tudo em dia!
        </p>
        <h2 className="mt-2 text-2xl font-bold text-zinc-900">
          Nenhuma revisão pendente
        </h2>
        <p className="mt-2 text-zinc-600">
          As questões deste material não estão vencidas para revisão no momento.
        </p>
      </section>
    );
  }

  if (!currentQuestion) {
    return (
      <section className="rounded-xl border border-zinc-200 bg-white p-8 text-center shadow-sm">
        <p className="text-sm font-medium text-zinc-500">
          Revisão concluída
        </p>
        <h2 className="mt-2 text-3xl font-bold text-zinc-900">
          Muito bem!
        </h2>
        <p className="mt-2 text-zinc-600">
          Acertos nesta sessão: {correctAnswers}
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-zinc-500">
          Revisão {currentIndex + 1}
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

          {currentQuestion.explanation && (
            <div className="mt-4 border-t border-zinc-200 pt-4">
              <p className="text-sm font-semibold text-zinc-700">
                Explicação
              </p>
              <p className="mt-1 text-sm leading-6 text-zinc-600">
                {currentQuestion.explanation}
              </p>
            </div>
          )}
        </div>
      )}

      {answered && (
        <button
          type="button"
          onClick={nextQuestion}
          className="mt-4 rounded-lg border border-zinc-300 px-5 py-3 font-medium text-zinc-900 hover:bg-zinc-50"
        >
          Próxima revisão
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
