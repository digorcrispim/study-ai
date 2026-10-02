"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { getUserId } from "@/lib/user";
import { updateLearningPlanItemStatus } from "@/lib/api";

type StudyQuestion = {
  id: string;
  question_text: string;
  options: Record<string, string>;
  difficulty: string | null;
  explanation: string | null;
};

type AdaptiveQuestion = {
  id: string;
  question_text: string;
  options: Record<string, string>;
  topics: string[];
  difficulty: string;
  explanation: string | null;
};

type StudyQuizProps = {
  questions: StudyQuestion[];
  materialId: string;
  topic?: string;
};

const SESSION_SIZE = 5;

export default function StudyQuiz({
  questions,
  materialId,
  topic,
}: StudyQuizProps) {
  const [studyQuestions, setStudyQuestions] = useState(questions);
  const [loadingQuestions, setLoadingQuestions] = useState(true);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionCompleted, setSessionCompleted] = useState(false);
  const loadingNext = false;
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null);
  const [result, setResult] = useState<boolean | null>(null);
  const [correctAnswers, setCorrectAnswers] = useState(0);
  const [answered, setAnswered] = useState(false);
  const [loading, setLoading] = useState(false);
  const [sessionAnsweredIds, setSessionAnsweredIds] = useState<string[]>([]);

  const searchParams = useSearchParams();
  const planItemId = searchParams.get("plan_item_id");
  const planItemStatusUpdated = useRef(false);
  const planItemCompleted = useRef(false);

  useEffect(() => {
    if (!planItemId || planItemStatusUpdated.current) {
      return;
    }

    planItemStatusUpdated.current = true;

    updateLearningPlanItemStatus(planItemId, "in_progress").catch((error) => {
      console.error("Failed to update plan item status:", error);
    });
  }, [planItemId]);

  useEffect(() => {
    if (!planItemId || !sessionCompleted || planItemCompleted.current) {
      return;
    }

    planItemCompleted.current = true;

    updateLearningPlanItemStatus(planItemId, "completed").catch((error) => {
      console.error("Failed to update plan item status:", error);
    });
  }, [planItemId, sessionCompleted]);

  useEffect(() => {
    let cancelled = false;

    async function loadAdaptiveQuestions() {
      try {
        const topicQuery =
          topic === undefined
            ? ""
            : `?topic=${encodeURIComponent(topic)}`;
        const response = await fetch(
          `/api/questions/material/${materialId}/adaptive/${getUserId()}${topicQuery}${topicQuery ? "&" : "?"}limit=5`,
          {
            cache: "no-store",
          }
        );

        if (!response.ok) {
          throw new Error("Não foi possível carregar a fila adaptativa.");
        }

        const data: StudyQuestion[] = await response.json();

        if (!cancelled && data.length > 0) {
          setStudyQuestions(data.slice(0, SESSION_SIZE));
          setCurrentIndex(0);
          const sessionResponse = await fetch(
            "/api/sessions",
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                user_id: getUserId(),
                material_id: materialId,
                mode: "study",
              }),
            }
          );

          if (!sessionResponse.ok) {
            throw new Error(
              "Não foi possível iniciar a sessão de estudo."
            );
          }

          const sessionData = await sessionResponse.json();
          setSessionId(sessionData.id);
        }
      } catch (error) {
        console.error(error);
      } finally {
        if (!cancelled) {
          setLoadingQuestions(false);
        }
      }
    }

    loadAdaptiveQuestions();

    return () => {
      cancelled = true;
    };
  }, [materialId, topic]);

  const currentQuestion = studyQuestions[currentIndex];
  const sessionTotal = Math.min(studyQuestions.length, SESSION_SIZE);

  const finished = currentIndex >= sessionTotal;
  useEffect(() => {
    if (!sessionId || !finished || sessionCompleted) {
      return;
    }

    async function completeSession() {
      try {
        const response = await fetch(
          `/api/sessions/${sessionId}/complete`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              total_questions: sessionTotal,
              correct_answers: correctAnswers,
            }),
          }
        );

        if (!response.ok) {
          throw new Error("Não foi possível concluir a sessão.");
        }

        setSessionCompleted(true);
      } catch (error) {
        console.error(error);
      }
    }

    completeSession();
  }, [
    sessionId,
    finished,
    sessionCompleted,
    sessionTotal,
    correctAnswers,
  ]);

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
      const topicQuery =
        topic === undefined
          ? ""
          : `?topic=${encodeURIComponent(topic)}`;
      const response = await fetch(
        `/api/questions/${currentQuestion.id}/answer${topicQuery}`,
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

      const adaptiveQuestions: AdaptiveQuestion[] =
        data.adaptive_questions ?? [];

      if (adaptiveQuestions.length > 0) {
        setStudyQuestions((currentQuestions) => {
          const answeredIds = new Set(sessionAnsweredIds);
          answeredIds.add(currentQuestion.id);

          const previousQuestions = currentQuestions.slice(
            0,
            currentIndex + 1
          );

          const adaptiveStudyQuestions: StudyQuestion[] =
            adaptiveQuestions.map((question) => ({
              id: question.id,
              question_text: question.question_text,
              options: question.options,
              difficulty: question.difficulty,
              explanation: question.explanation,
            }));

          const remainingQuestions = currentQuestions
            .slice(currentIndex + 1)
            .filter((question) => !answeredIds.has(question.id))
            .filter(
              (question) =>
                !adaptiveQuestions.some(
                  (adaptiveQuestion) =>
                    adaptiveQuestion.id === question.id
                )
            );

          const finalQuestions = [
            ...previousQuestions,
            ...adaptiveStudyQuestions,
            ...remainingQuestions,
          ].slice(0, SESSION_SIZE);

          return finalQuestions;
        });
      }

      setResult(data.is_correct);
      setAnswered(true);
      setSessionAnsweredIds((ids) => [...ids, currentQuestion.id]);

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
  const nextIndex = currentIndex + 1;

  if (nextIndex >= sessionTotal) {
    setCurrentIndex(nextIndex);
    return;
  }

  setCurrentIndex(nextIndex);
  setSelectedAnswer(null);
  setResult(null);
  setAnswered(false);

  }

  if (loadingQuestions) {
    return (
      <section className="rounded-xl border border-zinc-200 bg-white p-8 text-center shadow-sm">
        <p className="text-sm text-zinc-500">
          Preparando seu estudo personalizado...
        </p>
      </section>
    );
  }

  if (finished) {
    const total = sessionTotal;
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
              {sessionTotal}
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
          Questão {currentIndex + 1} de {sessionTotal}
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
          disabled={loadingNext}
          className="mt-4 rounded-lg border border-zinc-300 px-5 py-3 font-medium text-zinc-900 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loadingNext
            ? "Preparando próxima..."
            : currentIndex === sessionTotal - 1
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

