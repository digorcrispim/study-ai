export type PersistedLearningPlanItemResponse = {
  id: string;
  topic: string;
  material_id: string | null;
  action: string;
  priority: number;
  status: string;
  accuracy_snapshot: number | null;
  total_answers_snapshot: number | null;
  reason: string | null;
  created_at: string;
  completed_at: string | null;
};

export type PersistedLearningPlanResponse = {
  id: string;
  user_id: string;
  status: string;
  created_at: string;
  updated_at: string;
  items: PersistedLearningPlanItemResponse[];
};
