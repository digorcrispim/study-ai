import HomeButton from "../components/HomeButton";
import PerformanceDashboard from "./PerformanceDashboard";

export default function PerformancePage() {
  return (
    <main className="min-h-screen bg-zinc-50 p-8">
      <div className="mx-auto max-w-4xl">
        <header className="mb-8">
          <HomeButton />
          <h1 className="mt-4 text-3xl font-bold text-zinc-900">
            Meu desempenho
          </h1>

          <p className="mt-2 text-zinc-600">
            Acompanhe seu desempenho nas sessões de estudo.
          </p>
        </header>

        <PerformanceDashboard />
      </div>
    </main>
  );
}
