import type { PersistedLearningPlanResponse } from "@/lib/types";

export async function getCurrentLearningPlan(
  userId: string
): Promise<PersistedLearningPlanResponse> {
  const response = await fetch(`/api/learning-plan/${userId}/current`, {
    cache: "no-store",
  });

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
