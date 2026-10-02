import type { PersistedLearningPlanResponse } from "@/lib/types";

export async function getCurrentLearningPlan(
  userId: string
): Promise<PersistedLearningPlanResponse | null> {
  const response = await fetch(`/api/learning-plan/${userId}/current`, {
    cache: "no-store",
  });

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error("Failed to fetch learning plan");
  }

  return response.json();
}

export async function updateLearningPlanItemStatus(
  itemId: string,
  status: "pending" | "in_progress" | "completed"
): Promise<void> {
  const response = await fetch(`/api/learning-plan/items/${itemId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ status }),
  });

  if (!response.ok) {
    throw new Error("Failed to update learning plan item status");
  }
}

export async function generateLearningPlan(
  userId: string
): Promise<PersistedLearningPlanResponse> {
  const response = await fetch(`/api/learning-plan/${userId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error("Failed to generate learning plan");
  }

  return response.json();
}
