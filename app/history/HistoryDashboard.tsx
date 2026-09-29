"use client";

import { useEffect, useState } from "react";
import { getUserId } from "@/lib/user";

type StudySession = {
  id: string;
  user_id: string;
  material_id: string;
  mode: "study" | "review";
  started_at: string;
  completed_at: string | null;
  total_questions: number;
  correct_answers: number;
  accuracy: number;
};

type Material = {
  id: string;
  title: string;
};

export default function HistoryDashboard() {
  const [sessions, setSessions] = useState<StudySession[]>([]);
  const [filter, setFilter] = useState<"all" | "study" | "review">("all");
  const [materials, setMaterials] = useState<Material[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    async function loadHistory() {
      try {
        const userId = getUserId();

        const [sessionsResponse, materialsResponse] = await Promise.all([
          fetch(
            `http://127.0.0.1:8000/sessions/user/${userId}`,
            {
              cache: "no-store",
            }
          ),
          fetch("http://127.0.0.1:8000/materials", {
            cache: "no-store",
          }),
        ]);

        if (!sessionsResponse.ok || !materialsResponse.ok) {
          throw new Error("Não foi possível carregar o histórico.");
        }

        const sessionsData: StudySession[] =
          await sessionsResponse.json();

        const materialsData: Material[] =
          await materialsResponse.json();

        setSessions(sessionsData);
        setMaterials(materialsData);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    }

    loadHistory();
  }, []);

  const completedSessions = sessions.filter(
    (session) => session.completed_at !== null
  );

  const filteredSessions = completedSessions.filter(
    (session) => filter === "all" || session.mode === filter
  );
  const totalQuestions = completedSessions.reduce(
    (total, session) => total + session.total_questions,
    0
  );

  const totalCorrectAnswers = completedSessions.reduce(
    (total, session) => total + session.correct_answers,
    0
  );

  const overallAccuracy =
    totalQuestions > 0
      ? (totalCorrectAnswers / totalQuestions) * 100
      : 0;

  const studySessions = completedSessions.filter(
    (session) => session.mode === "study"
  ).length;

  const reviewSessions = completedSessions.filter(
    (session) => session.mode === "review"
  ).length;

  const materialPerformance = completedSessions.reduce(
    (groups, session) => {
      const existing = groups.find(
        (item) => item.material_id === session.material_id
      );

      if (existing) {
        existing.sessions += 1;
        existing.total_questions += session.total_questions;
        existing.correct_answers += session.correct_answers;

        if (session.mode === "study") {
          existing.study_sessions += 1;
        } else {
          existing.review_sessions += 1;
        }
      } else {
        groups.push({
          material_id: session.material_id,
          sessions: 1,
          total_questions: session.total_questions,
          correct_answers: session.correct_answers,
          study_sessions: session.mode === "study" ? 1 : 0,
          review_sessions: session.mode === "review" ? 1 : 0,
        });
      }

      return groups;
    },
    [] as Array<{
      material_id: string;
      sessions: number;
      total_questions: number;
      correct_answers: number;
      study_sessions: number;
      review_sessions: number;
    }>
  );

  function getMaterialTitle(materialId: string) {
    const material = materials.find(
      (item) => item.id === materialId
    );

    return material?.title ?? "Material não encontrado";
  }

  function formatDate(date: string) {
    return new Date(date).toLocaleString("pt-BR", {
      dateStyle: "short",
      timeStyle: "short",
    });
  }

  if (loading) {
    return (
      <div className="rounded-xl bg-white p-6 shadow-sm">
        Carregando histórico...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-dashed border-zinc-300 bg-white p-6 text-zinc-500">
        Não foi possível carregar o histórico.
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-zinc-300 bg-white p-8 text-center text-zinc-500">
        Ainda não há sessões de estudo registradas.
      </div>
    );
  }

  return (
    <div className="space-y-6">
           <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl bg-white p-5 shadow-sm">
          <p className="text-sm text-zinc-500">Sessões concluídas</p>
          <p className="mt-2 text-3xl font-bold text-zinc-900">
            {completedSessions.length}
          </p>
        </div>

        <div className="rounded-xl bg-white p-5 shadow-sm">
          <p className="text-sm text-zinc-500">Questões respondidas</p>
          <p className="mt-2 text-3xl font-bold text-zinc-900">
            {totalQuestions}
          </p>
        </div>

        <div className="rounded-xl bg-white p-5 shadow-sm">
          <p className="text-sm text-zinc-500">Acertos</p>
          <p className="mt-2 text-3xl font-bold text-zinc-900">
            {totalCorrectAnswers}
          </p>
        </div>

        <div className="rounded-xl bg-white p-5 shadow-sm">
          <p className="text-sm text-zinc-500">Precisão geral</p>
          <p className="mt-2 text-3xl font-bold text-zinc-900">
            {overallAccuracy.toFixed(1)}%
          </p>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl bg-white p-5 shadow-sm">
          <p className="text-sm text-zinc-500">Sessões de estudo</p>
          <p className="mt-2 text-2xl font-bold text-zinc-900">
            {studySessions}
          </p>
        </div>

        <div className="rounded-xl bg-white p-5 shadow-sm">
          <p className="text-sm text-zinc-500">Sessões de revisão</p>
          <p className="mt-2 text-2xl font-bold text-zinc-900">
            {reviewSessions}
          </p>
        </div>
      </div>
      <section className="space-y-4">
        <h2 className="text-xl font-semibold">Desempenho por material</h2>

        {materialPerformance.length === 0 ? (
          <p className="text-sm text-gray-500">
            Ainda não há desempenho registrado por material.
          </p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {materialPerformance.map((item) => {
              const accuracy =
                item.total_questions > 0
                  ? (item.correct_answers / item.total_questions) * 100
                  : 0;

              return (
                <article
                  key={item.material_id}
                  className="space-y-3 rounded-xl border p-4"
                >
                  <h3 className="font-semibold">
                    {getMaterialTitle(item.material_id)}
                  </h3>

                  <p className="text-sm text-gray-500">
                    {item.sessions} sessões concluídas
                  </p>

                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <p className="text-gray-500">Questões</p>
                      <p className="text-lg font-semibold">
                        {item.total_questions}
                      </p>
                    </div>

                    <div>
                      <p className="text-gray-500">Acertos</p>
                      <p className="text-lg font-semibold">
                        {item.correct_answers}
                      </p>
                    </div>

                    <div>
                      <p className="text-gray-500">Precisão</p>
                      <p className="text-lg font-semibold">
                        {accuracy.toFixed(1)}%
                      </p>
                    </div>

                    <div>
                      <p className="text-gray-500">Estudo / Revisão</p>
                      <p className="text-lg font-semibold">
                        {item.study_sessions} / {item.review_sessions}
                      </p>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setFilter("all")}
          className={`rounded-lg px-4 py-2 text-sm font-medium ${
            filter === "all"
              ? "bg-zinc-900 text-white"
              : "border border-zinc-300 bg-white text-zinc-900 hover:bg-zinc-50"
          }`}
        >
          Todas
        </button>

        <button
          type="button"
          onClick={() => setFilter("study")}
          className={`rounded-lg px-4 py-2 text-sm font-medium ${
            filter === "study"
              ? "bg-zinc-900 text-white"
              : "border border-zinc-300 bg-white text-zinc-900 hover:bg-zinc-50"
          }`}
        >
          Estudo
        </button>

        <button
          type="button"
          onClick={() => setFilter("review")}
          className={`rounded-lg px-4 py-2 text-sm font-medium ${
            filter === "review"
              ? "bg-zinc-900 text-white"
              : "border border-zinc-300 bg-white text-zinc-900 hover:bg-zinc-50"
          }`}
        >
          Revisão
        </button>
      </div>

      {filteredSessions.map((session) => (
        <article
          key={session.id}
          className="rounded-xl bg-white p-5 shadow-sm"
        >
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-zinc-900">
                {getMaterialTitle(session.material_id)}
              </h2>

              <p className="mt-1 text-sm text-zinc-500">
                {session.mode === "study"
                  ? "Modo de estudo"
                  : "Modo de revisão"}
              </p>

              <p className="mt-1 text-sm text-zinc-500">
                Início: {formatDate(session.started_at)}
              </p>
            </div>

            <div className="grid grid-cols-3 gap-3 text-center">
              <div>
                <p className="text-xs text-zinc-500">Questões</p>
                <p className="mt-1 text-lg font-bold text-zinc-900">
                  {session.total_questions}
                </p>
              </div>

              <div>
                <p className="text-xs text-zinc-500">Acertos</p>
                <p className="mt-1 text-lg font-bold text-zinc-900">
                  {session.correct_answers}
                </p>
              </div>

              <div>
                <p className="text-xs text-zinc-500">Precisão</p>
                <p className="mt-1 text-lg font-bold text-zinc-900">
                  {session.accuracy.toFixed(1)}%
                </p>
              </div>
            </div>
          </div>

          <div className="mt-4 border-t border-zinc-100 pt-4">
            {session.completed_at ? (
              <p className="text-sm text-zinc-500">
                Concluída em {formatDate(session.completed_at)}
              </p>
            ) : (
              <p className="text-sm text-zinc-500">
                Sessão não concluída
              </p>
            )}
          </div>
        </article>
      ))}
    </div>
  );
}

