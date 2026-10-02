import HomeButton from "../components/HomeButton";
import LearningPlanDashboard from "../components/LearningPlanDashboard";

export default function LearningPlanPage() {
  return (
    <main className="min-h-screen bg-zinc-50 p-8">
      <div className="mx-auto max-w-4xl">
        <header className="mb-8">
          <HomeButton />
          <h1 className="mt-4 text-3xl font-bold text-zinc-900">
            Plano de aprendizagem
          </h1>

          <p className="mt-2 text-zinc-600">
            Acompanhe o estado e o progresso dos itens do seu plano.
          </p>
        </header>

        <LearningPlanDashboard />
      </div>
    </main>
  );
}
