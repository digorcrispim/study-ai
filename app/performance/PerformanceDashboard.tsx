"use client";

import { useEffect, useState } from "react";
import { getUserId } from "@/lib/user";

type Summary = {
  user_id: string;
  total_answers: number;
  correct_answers: number;
  incorrect_answers: number;
  accuracy: number;
};

type TopicPerformance = {
  topic: string;
  total_answers: number;
  correct_answers: number;
  incorrect_answers: number;
  accuracy: number;
};

type TopicResponse = {
  user_id: string;
  topics: TopicPerformance[];
};

export default function PerformanceDashboard() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [topics, setTopics] = useState<TopicPerformance[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    async function loadPerformance() {
      try {
        const userId = getUserId();

        const [summaryResponse, topicsResponse] = await Promise.all([
          fetch(
            `http://127.0.0.1:8000/questions/user/${userId}/summary`
          ),
          fetch(
            `http://127.0.0.1:8000/questions/user/${userId}/topics`
          ),
        ]);

        if (!summaryResponse.ok || !topicsResponse.ok) {
          throw new Error("Não foi possível carregar o desempenho.");
        }

        const summaryData: Summary = await summaryResponse.json();
        const topicsData: TopicResponse = await topicsResponse.json();

        setSummary(summaryData);
        setTopics(topicsData.topics);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    }

    loadPerformance();
  }, []);

  if (loading) {
    return (
      <div className="rounded-xl bg-white p-6 shadow-sm">
        Carregando desempenho...
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="rounded-xl border border-dashed border-zinc-300 bg-white p-6 text-zinc-500">
        Não foi possível carregar o desempenho.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl bg-white p-5 shadow-sm">
          <p className="text-sm text-zinc-500">Respondidas</p>
          <p className="mt-2 text-3xl font-bold">
            {summary.total_answers}
          </p>
        </div>

        <div className="rounded-xl bg-white p-5 shadow-sm">
          <p className="text-sm text-zinc-500">Acertos</p>
          <p className="mt-2 text-3xl font-bold">
            {summary.correct_answers}
          </p>
        </div>

        <div className="rounded-xl bg-white p-5 shadow-sm">
          <p className="text-sm text-zinc-500">Erros</p>
          <p className="mt-2 text-3xl font-bold">
            {summary.incorrect_answers}
          </p>
        </div>

        <div className="rounded-xl bg-white p-5 shadow-sm">
          <p className="text-sm text-zinc-500">Precisão</p>
          <p className="mt-2 text-3xl font-bold">
            {summary.accuracy.toFixed(1)}%
          </p>
        </div>
      </div>

      <section className="rounded-xl bg-white p-6 shadow-sm">
        <div>
          <p className="text-sm font-medium text-zinc-500">
            Desempenho por tópico
          </p>

          <h2 className="mt-1 text-xl font-semibold text-zinc-900">
            Onde você está acertando e errando
          </h2>
        </div>

        {topics.length === 0 ? (
          <p className="mt-6 text-zinc-500">
            Ainda não há respostas suficientes para mostrar o desempenho por tópico.
          </p>
        ) : (
          <div className="mt-6 space-y-4">
            {topics.map((topic) => (
              <div
                key={topic.topic}
                className="rounded-lg border border-zinc-200 p-4"
              >
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="font-medium text-zinc-900">
                      {topic.topic}
                    </p>
                    <p className="text-sm text-zinc-500">
                      {topic.total_answers} respostas ·{" "}
                      {topic.correct_answers} acertos ·{" "}
                      {topic.incorrect_answers} erros
                    </p>
                  </div>

                  <p className="text-lg font-bold text-zinc-900">
                    {topic.accuracy.toFixed(1)}%
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
