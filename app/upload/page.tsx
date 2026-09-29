import Link from "next/link";
import UploadForm from "./UploadForm";

export default function UploadPage() {
  return (
    <main className="min-h-screen bg-zinc-50 p-8">
      <div className="mx-auto max-w-4xl">
        <header className="mb-8">
          <Link
            href="/"
            className="text-sm font-medium text-zinc-500 hover:text-zinc-900"
          >
            ← Voltar para materiais
          </Link>

          <h1 className="mt-4 text-3xl font-bold text-zinc-900">
            Adicionar material
          </h1>

          <p className="mt-2 text-zinc-600">
            Envie um PDF para começar a criar seu material de estudo.
          </p>
        </header>

        <UploadForm />
      </div>
    </main>
  );
}
