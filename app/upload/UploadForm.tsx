"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const ACCEPTED_TYPES = [
  "application/pdf",
  "text/plain",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "video/mp4",
  "video/x-matroska",
  "video/x-msvideo",
  "video/quicktime",
  "video/webm",
];

const ACCEPT_ATTR = ".pdf,.txt,.docx,.mp4,.mkv,.avi,.mov,.webm";

// webkitdirectory/directory não fazem parte do tipo padrão de <input> no
// React, então aplicamos via spread type-safe para não quebrar o typecheck.
// IMPORTANTE: o valor precisa ser uma string truthy ("true") — o React
// omite do DOM atributos desconhecidos cujo valor é falsy (ex.: ""), o que
// faria o seletor de pasta não funcionar.
const directoryInputProps = {
  webkitdirectory: "true",
  directory: "true",
} as unknown as React.InputHTMLAttributes<HTMLInputElement>;

export default function UploadForm() {
  const router = useRouter();

  const [title, setTitle] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [fromFolder, setFromFolder] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  function selectFiles(fileList: FileList | null, folder: boolean) {
    setError("");
    setSuccess(false);
    setFromFolder(folder);

    if (!fileList || fileList.length === 0) {
      setFiles([]);
      return;
    }

    const validFiles = Array.from(fileList).filter((file) =>
      ACCEPTED_TYPES.includes(file.type)
    );

    setFiles(validFiles);

    if (validFiles.length === 0) {
      setError(
        "Nenhum arquivo compatível selecionado. Formatos aceitos: PDF, " +
          "TXT, DOCX ou vídeo (MP4, MKV, AVI, MOV, WEBM)."
      );
    }
  }

  async function uploadOneFile(file: File, fileTitle: string): Promise<void> {
    const formData = new FormData();
    formData.append("title", fileTitle);
    formData.append("file", file);

    const uploadResponse = await fetch("/api/materials/upload-pdf", {
      method: "POST",
      body: formData,
    });

    if (!uploadResponse.ok) {
      const data = await uploadResponse.json().catch(() => null);
      throw new Error(data?.detail || "Não foi possível enviar o arquivo.");
    }

    const material = await uploadResponse.json();

    // Gerar questões (passo não-bloqueante): o material já foi criado,
    // então uma falha aqui não impede o sucesso do upload.
    try {
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
        console.warn(
          "Question generation failed, but material was created successfully"
        );
      }
    } catch (generationError) {
      console.warn("Question generation error:", generationError);
    }
  }

  function titleForFile(file: File, index: number): string {
    // Em modo pasta, o título vem do nome do arquivo (sem extensão).
    // Em modo arquivo único, usa o título informado pelo usuário.
    if (fromFolder) {
      const base = file.name.replace(/\.[^.]+$/, "");
      return base || `Material ${index + 1}`;
    }
    return title;
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (loading || files.length === 0) {
      return;
    }

    // Em modo arquivo único, o título é obrigatório.
    if (!fromFolder && !title) {
      return;
    }

    setLoading(true);
    setError("");
    setSuccess(false);

    try {
      for (let index = 0; index < files.length; index += 1) {
        await uploadOneFile(files[index], titleForFile(files[index], index));
      }

      setSuccess(true);
      router.push("/");
      router.refresh();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Não foi possível processar o(s) material(is)."
      );
    } finally {
      setLoading(false);
    }
  }

  const canSubmit =
    files.length > 0 &&
    !loading &&
    !success &&
    (fromFolder || Boolean(title));

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
          disabled={fromFolder}
          className="mt-2 w-full rounded-lg border border-zinc-300 px-4 py-3 outline-none focus:border-zinc-500 disabled:bg-zinc-100 disabled:text-zinc-400"
        />
        {fromFolder && (
          <p className="mt-2 text-sm text-zinc-500">
            No modo pasta, o título de cada material vem do nome do arquivo.
          </p>
        )}
      </div>

      <div>
        <span className="block text-sm font-medium text-zinc-700">
          Enviar (PDF, TXT, DOCX ou vídeo)
        </span>

        <div className="mt-2 flex gap-2">
          <label className="flex-1 cursor-pointer">
            <input
              type="file"
              accept={ACCEPT_ATTR}
              className="hidden"
              onChange={(event) => selectFiles(event.target.files, false)}
            />
            <div className="rounded-lg bg-blue-500 px-4 py-2 text-center font-medium text-white hover:bg-blue-600">
              📄 Arquivo
            </div>
          </label>

          <label className="flex-1 cursor-pointer">
            <input
              type="file"
              multiple
              accept={ACCEPT_ATTR}
              className="hidden"
              onChange={(event) => selectFiles(event.target.files, true)}
              {...directoryInputProps}
            />
            <div className="rounded-lg bg-green-500 px-4 py-2 text-center font-medium text-white hover:bg-green-600">
              📁 Pasta
            </div>
          </label>
        </div>

        {files.length > 0 && (
          <p className="mt-2 text-sm text-zinc-500">
            {fromFolder
              ? `${files.length} arquivo(s) selecionado(s) da pasta`
              : `Arquivo selecionado: ${files[0].name}`}
          </p>
        )}
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {success && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
          Material(is) adicionado(s) com sucesso. Redirecionando para seus
          materiais...
        </div>
      )}

      <button
        type="submit"
        disabled={!canSubmit}
        className="rounded-lg bg-zinc-900 px-5 py-3 font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? "Processando material(is)..." : "Enviar"}
      </button>
    </form>
  );
}
