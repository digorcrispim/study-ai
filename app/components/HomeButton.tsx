import Link from "next/link";

export default function HomeButton() {
  return (
    <div className="flex flex-wrap gap-4">
      <Link
        href="/"
        className="inline-block rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-medium text-zinc-900 hover:bg-zinc-50"
      >
        Home
      </Link>

      <Link
        href="/learning-plan"
        className="inline-block rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-medium text-zinc-900 hover:bg-zinc-50"
      >
        Plano de Aprendizagem
      </Link>
    </div>
  );
}
