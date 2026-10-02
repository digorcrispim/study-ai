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
