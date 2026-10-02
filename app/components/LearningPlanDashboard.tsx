"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getUserId } from "@/lib/user";
import { getCurrentLearningPlan, generateLearningPlan } from "@/lib/api";
import type {
  PersistedLearningPlanItemResponse,
  PersistedLearningPlanResponse,
} from "@/lib/types";

const actionGroups: { action: string; label: string }[] = [
  { action: "reinforce", label: "Reforçar" },
  { action: "consolidate", label: "Consolidar" },
  { action: "deepen", label: "Aprofundar" },
  { action: "explore", label: "Explorar" },
];

const actionLabels: Record<string, string> = {
  reinforce: "Reforçar",
  consolidate: "Consolidar",
  deepen: "Aprofundar",
  explore: "Explorar",
};

const statusLabels: Record<string, string> = {
  pending: "Pendente",
  in_progress: "Em andamento",
  completed: "Concluído",
};

const statusBadgeClasses: Record<string, string> = {
  pending: "border-zinc-300 bg-zinc-50 text-zinc-600",
  in_progress: "border-amber-300 bg-amber-50 text-amber-800",
  completed: "border-emerald-300 bg-emerald-50 text-emerald-800",
};

function StatusBadge({ status }: { status: string }) {
  const label = statusLabels[status] ?? status;
  const classes =
    statusBadgeClasses[status] ?? "border-zinc-300 bg-zinc-50 text-zinc-600";

  return (
    <span
      className={`inline-block rounded-full border px-3 py-1 text-xs font-medium ${classes}`}
    >
      {label}
    </span>
  );
}

function formatDate(value: string | null): string | null {
  if (!value) {
    return null;
  }

  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return null;
  }

  return parsed.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function PlanItemCard({
  item,
}: {
  item: PersistedLearningPlanItemResponse;
}) {
  const completedAt = formatDate(item.completed_at);

  return (
    <article className="rounded-lg border border-zinc-200 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="font-medium text-zinc-900">{item.topic}</p>
          <p className="mt-1 text-sm text-zinc-500">
            {item.total_answers_snapshot !== null && (
              <>{item.total_answers_snapshot} respostas</>
            )}
            {item.accuracy_snapshot !== null && (
              <>
                {item.total_answers_snapshot !== null && " · "}
                {item.accuracy_snapshot.toFixed(1)}% de precisão
              </>
            )}
          </p>
          {item.reason && (
            <p className="mt-2 text-sm text-zinc-600">{item.reason}</p>
          )}
          {completedAt && (
            <p className="mt-2 text-sm text-zinc-500">
              Concluído em {completedAt}
            </p>
          )}
          {item.material_id !== null && (
            <Link
              href={`/materials/${item.material_id}?topic=${encodeURIComponent(item.topic)}&plan_item_id=${item.id}`}
              className="mt-3 inline-block rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800"
            >
              Estudar este tópico
            </Link>
          )}
        </div>

        <div className="sm:shrink-0">
          <StatusBadge status={item.status} />
        </div>
      </div>
    </article>
  );
}

export default function LearningPlanDashboard() {
  const [plan, setPlan] = useState<PersistedLearningPlanResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState(false);

  useEffect(() => {
    async function loadPlan() {
      try {
        const userId = getUserId();
        const planData = await getCurrentLearningPlan(userId);
        setPlan(planData);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    }

    loadPlan();
  }, []);

  async function handleGeneratePlan() {
    if (generating) {
      return;
    }

    setGenerating(true);
    setGenerateError(false);

    try {
      const userId = getUserId();
      const planData = await generateLearningPlan(userId);
      setPlan(planData);
    } catch {
      setGenerateError(true);
    } finally {
      setGenerating(false);
    }
  }

  if (loading) {
    return (
      <div className="rounded-xl bg-white p-6 shadow-sm">
        Carregando plano de aprendizagem...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-dashed border-zinc-300 bg-white p-6 text-zinc-500">
        Não foi possível carregar o plano de aprendizagem.
      </div>
    );
  }

  if (!plan) {
    return (
      <div className="rounded-xl border border-dashed border-zinc-300 bg-white p-6">
        <p className="text-zinc-600">
          Você ainda não possui um plano de aprendizagem.
        </p>

        <button
          type="button"
          onClick={handleGeneratePlan}
          disabled={generating}
          className="mt-4 rounded-lg bg-zinc-900 px-5 py-3 font-medium text-white hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {generating
            ? "Gerando seu plano..."
            : "Gerar meu plano de aprendizagem"}
        </button>

        {generateError && (
          <p className="mt-4 text-sm text-red-600">
            Não foi possível gerar o plano de aprendizagem. Tente novamente.
          </p>
        )}
      </div>
    );
  }

  const total = plan.items.length;
  const completed = plan.items.filter(
    (item) => item.status === "completed"
  ).length;
  const inProgress = plan.items.filter(
    (item) => item.status === "in_progress"
  ).length;
  const pending = plan.items.filter(
    (item) => item.status === "pending"
  ).length;
  const updatedAt = formatDate(plan.updated_at);

  const sortedItems = [...plan.items].sort(
    (first, second) => first.priority - second.priority
  );

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl bg-white p-5 shadow-sm">
          <p className="text-sm text-zinc-500">Itens</p>
          <p className="mt-2 text-3xl font-bold">{total}</p>
        </div>

        <div className="rounded-xl bg-white p-5 shadow-sm">
          <p className="text-sm text-zinc-500">Concluídos</p>
          <p className="mt-2 text-3xl font-bold">{completed}</p>
        </div>

        <div className="rounded-xl bg-white p-5 shadow-sm">
          <p className="text-sm text-zinc-500">Em andamento</p>
          <p className="mt-2 text-3xl font-bold">{inProgress}</p>
        </div>

        <div className="rounded-xl bg-white p-5 shadow-sm">
          <p className="text-sm text-zinc-500">Pendentes</p>
          <p className="mt-2 text-3xl font-bold">{pending}</p>
        </div>
      </div>

      <section className="rounded-xl bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-xl font-semibold text-zinc-900">
            Itens do plano
          </h2>
          {updatedAt && (
            <p className="text-sm text-zinc-500">
              Atualizado em {updatedAt}
            </p>
          )}
        </div>

        {total === 0 ? (
          <p className="mt-4 text-zinc-500">
            Este plano ainda não possui itens.
          </p>
        ) : (
          <div className="mt-5 space-y-6">
            {actionGroups.map((group) => {
              const items = sortedItems.filter(
                (item) => item.action === group.action
              );

              if (items.length === 0) {
                return null;
              }

              return (
                <div key={group.action}>
                  <h3 className="text-sm font-semibold text-zinc-700">
                    {group.label}
                  </h3>
                  <div className="mt-2 space-y-3">
                    {items.map((item) => (
                      <PlanItemCard key={item.id} item={item} />
                    ))}
                  </div>
                </div>
              );
            })}

            {sortedItems.some(
              (item) => !(item.action in actionLabels)
            ) && (
              <div>
                <h3 className="text-sm font-semibold text-zinc-700">
                  Outros
                </h3>
                <div className="mt-2 space-y-3">
                  {sortedItems
                    .filter((item) => !(item.action in actionLabels))
                    .map((item) => (
                      <PlanItemCard key={item.id} item={item} />
                    ))}
                </div>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
