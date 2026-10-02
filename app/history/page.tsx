import HomeButton from "../components/HomeButton";
import HistoryDashboard from "./HistoryDashboard";

export default function HistoryPage() {
  return (
    <main className="min-h-screen bg-zinc-50 p-8">
      <div className="mx-auto max-w-4xl">
        <header className="mb-8">
          <HomeButton />
          <h1 className="mt-4 text-3xl font-bold text-zinc-900">
            Histórico de estudos
          </h1>

          <p className="mt-2 text-zinc-600">
            Consulte suas sessões de estudo e revisão.
          </p>
        </header>

        <HistoryDashboard />
      </div>
    </main>
  );
}
