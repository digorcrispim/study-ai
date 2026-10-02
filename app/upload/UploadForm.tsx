"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function UploadForm() {
  const router = useRouter();

  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(
    event: React.FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    if (!title || !file || loading) {
      return;
    }

    setLoading(true);
    setError("");

    try {
      const formData = new FormData();

      formData.append("title", title);
      formData.append("file", file);

      const uploadResponse = await fetch(
        "/api/materials/upload-pdf",
        {
          method: "POST",
          body: formData,
        }
      );

      if (!uploadResponse.ok) {
        const data = await uploadResponse.json().catch(() => null);

        throw new Error(
          data?.detail || "Não foi possível enviar o PDF."
        );
      }

      const material = await uploadResponse.json();

      const generationResponse = await fetch(
        `/api/materials/${material.id}/generate-questions`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            number_of_questions: 5,
          }),
        }
      );

      if (!generationResponse.ok) {
        const data = await generationResponse.json().catch(() => null);

        throw new Error(
          data?.detail ||
            "O PDF foi enviado, mas não foi possível gerar as questões."
        );
      }

      router.push(`/materials/${material.id}`);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Não foi possível processar o material."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-6 rounded-xl border border-zinc-200 bg-white p-6 shadow-sm"
    >
      <div>
        <label
          htmlFor="title"
          className="block text-sm font-medium text-zinc-700"
        >
          Título do material
        </label>

        <input
          id="title"
          type="text"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="Ex.: Microeconomia 1"
          className="mt-2 w-full rounded-lg border border-zinc-300 px-4 py-3 outline-none focus:border-zinc-500"
        />
      </div>

      <div>
        <label
          htmlFor="file"
          className="block text-sm font-medium text-zinc-700"
        >
          Arquivo PDF
        </label>

        <input
          id="file"
          type="file"
          accept="application/pdf"
          onChange={(event) => {
            setFile(event.target.files?.[0] ?? null);
          }}
          className="mt-2 block w-full text-sm text-zinc-600"
        />

        {file && (
          <p className="mt-2 text-sm text-zinc-500">
            Arquivo selecionado: {file.name}
          </p>
        )}
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={!title || !file || loading}
        className="rounded-lg bg-zinc-900 px-5 py-3 font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? "Processando material..." : "Enviar PDF"}
      </button>
    </form>
  );
}
