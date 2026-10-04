"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const ACCEPTED_TYPES = [
  "application/pdf",
  "text/plain",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document", // .docx
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", // .xlsx
  "application/vnd.openxmlformats-officedocument.presentationml.presentation", // .pptx
  "application/vnd.oasis.opendocument.text", // .odt
  "application/vnd.oasis.opendocument.spreadsheet", // .ods
  "application/vnd.oasis.opendocument.presentation", // .odp
  "video/mp4",
  "video/x-matroska",
  "video/x-msvideo",
  "video/quicktime",
  "video/webm",
];

const ACCEPT_ATTR =
  ".pdf,.txt,.docx,.xlsx,.pptx,.odt,.ods,.odp,.mp4,.mkv,.avi,.mov,.webm";

export default function UploadForm() {
  const router = useRouter();

  const [title, setTitle] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [transcriptionProgress, setTranscriptionProgress] = useState("");

  // Título personalizado só faz sentido quando há exatamente um arquivo.
  const singleFile = files.length === 1;

  function handleFileSelect(event: React.ChangeEvent<HTMLInputElement>) {
    setError("");
    setSuccess(false);

    const fileList = event.target.files;
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

    // Timeout de 15 min: transcrição de vídeos longos pode ser demorada
    // (margem de segurança; mais rápido quando há GPU no backend).
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 900000);

    if (file.type.startsWith("video/")) {
      setTranscriptionProgress(
        "Transcrevendo vídeo... isso pode levar alguns minutos."
      );
    }

    let uploadResponse: Response;
    try {
      uploadResponse = await fetch("/api/materials/upload-pdf", {
        method: "POST",
        body: formData,
        signal: controller.signal,
      });
    } catch (fetchError) {
      if (
        fetchError instanceof DOMException &&
        fetchError.name === "AbortError"
      ) {
        throw new Error(
          "Tempo esgotado: o processamento do arquivo demorou demais " +
            "(vídeos longos podem exceder o limite). Tente um arquivo menor."
        );
      }
      throw new Error(
        "Falha de conexão ao enviar o arquivo. Verifique sua rede e tente novamente."
      );
    } finally {
      clearTimeout(timeoutId);
      setTranscriptionProgress("");
    }

    if (!uploadResponse.ok) {
      const data = await uploadResponse.json().catch(() => null);
      const errorMsg =
        data?.detail ||
        (uploadResponse.status === 413
          ? "Arquivo muito grande."
          : uploadResponse.status === 408
            ? "Tempo esgotado — tente um arquivo menor."
            : `Erro ${uploadResponse.status}: ${uploadResponse.statusText}`);
      throw new Error(errorMsg);
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
    // Com um único arquivo e título informado, usa o título do usuário.
    // Caso contrário, deriva do nome do arquivo (sem extensão).
    if (singleFile && title) {
      return title;
    }
    const base = file.name.replace(/\.[^.]+$/, "");
    return base || `Material ${index + 1}`;
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (loading || files.length === 0) {
      return;
    }

    // Com um único arquivo, o título é obrigatório.
    if (singleFile && !title) {
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
    (!singleFile || Boolean(title));

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
          disabled={!singleFile}
          className="mt-2 w-full rounded-lg border border-zinc-300 px-4 py-3 outline-none focus:border-zinc-500 disabled:bg-zinc-100 disabled:text-zinc-400"
        />
        {files.length > 1 && (
          <p className="mt-2 text-sm text-zinc-500">
            Com vários arquivos, o título de cada material vem do nome do
            arquivo.
          </p>
        )}
      </div>

      <div>
        <span className="block text-sm font-medium text-zinc-700">
          Arquivos (PDF, TXT, DOCX ou vídeo)
        </span>

        <label className="mt-2 block cursor-pointer">
          <input
            type="file"
            multiple
            accept={ACCEPT_ATTR}
            className="hidden"
            onChange={handleFileSelect}
          />
          <div className="rounded-lg bg-blue-500 px-6 py-3 text-center font-medium text-white hover:bg-blue-600">
            📁 Selecionar Arquivos
          </div>
        </label>

        {files.length > 0 && (
          <p className="mt-2 text-sm text-zinc-500">
            {singleFile
              ? `Arquivo selecionado: ${files[0].name}`
              : `${files.length} arquivo(s) selecionado(s)`}
          </p>
        )}
      </div>

      {transcriptionProgress && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-700">
          {transcriptionProgress}
        </div>
      )}

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
