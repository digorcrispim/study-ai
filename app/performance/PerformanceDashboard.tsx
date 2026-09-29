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

export default function PerformanceDashboard() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    async function loadSummary() {
      try {
        const userId = getUserId();

        const response = await fetch(
          `http://127.0.0.1:8000/questions/user/${userId}/summary`
        );

        if (!response.ok) {
          throw new Error("Não foi possível carregar o desempenho.");
        }

        const data = await response.json();
        setSummary(data);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    }

    loadSummary();
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
  );
}
