import { useState, useRef, useCallback, useEffect } from "react";
import type { FileInfo, UploadResponse } from "../types";

interface FileUploadProps {
  onUploaded?: (filename: string) => void;
}

export default function FileUpload({ onUploaded }: FileUploadProps) {
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // Load existing files on mount
  const loadFiles = useCallback(async () => {
    try {
      const res = await fetch("/v3/files");
      if (res.ok) {
        const data = await res.json();
        setFiles(data.files || []);
      }
    } catch {
      // Silently fail - the server may not be ready
    }
  }, []);

  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
  }

  async function uploadFile(file: File) {
    setError("");
    setSuccessMsg("");
    setUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch("/v3/upload", {
        method: "POST",
        body: formData,
      });

      const data: UploadResponse = await res.json();

      if (data.success) {
        setSuccessMsg(`${data.filename} 上传成功`);
        onUploaded?.(data.filename || file.name);
        loadFiles();
      } else {
        setError(data.error || "上传失败");
      }
    } catch {
      setError("网络错误，上传失败");
    } finally {
      setUploading(false);
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.name.endsWith(".html")) {
      uploadFile(droppedFile);
    } else {
      setError("只支持 .html 文件");
    }
  }

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0];
    if (selected) uploadFile(selected);
    // Reset so same file re-selection works
    e.target.value = "";
  }

  return (
    <div className="border-t border-gray-200 bg-gray-50 p-4">
      {/* Upload zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors ${
          dragging
            ? "border-green-500 bg-green-50"
            : uploading
            ? "border-gray-300 bg-gray-100 pointer-events-none"
            : "border-gray-300 hover:border-green-400 hover:bg-green-50/50"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".html"
          onChange={handleInputChange}
          className="hidden"
        />
        {uploading ? (
          <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
            <span className="inline-block w-4 h-4 border-2 border-green-500 border-t-transparent rounded-full animate-spin" />
            上传中...
          </div>
        ) : (
          <div className="text-sm text-gray-500">
            <p className="font-medium text-gray-700">
              拖拽 SOP 文档到此处，或点击选择文件
            </p>
            <p className="text-xs mt-1">仅支持 .html 文件，最大 10MB</p>
          </div>
        )}
      </div>

      {/* Status messages */}
      {error && (
        <div className="mt-2 text-xs text-red-600 bg-red-50 rounded px-3 py-1.5">
          {error}
        </div>
      )}
      {successMsg && (
        <div className="mt-2 text-xs text-green-600 bg-green-50 rounded px-3 py-1.5">
          {successMsg}
        </div>
      )}

      {/* File list */}
      {files.length > 0 && (
        <div className="mt-3">
          <p className="text-xs font-medium text-gray-500 mb-1.5">
            data/ 目录现有文件 ({files.length})
          </p>
          <div className="max-h-32 overflow-y-auto space-y-1">
            {files.map((f) => (
              <div
                key={f.name}
                className="flex items-center justify-between text-xs bg-white rounded px-2 py-1 border border-gray-200"
              >
                <span className="text-gray-700 font-mono truncate mr-2" title={f.name}>
                  {f.name}
                </span>
                <span className="text-gray-400 shrink-0">{formatSize(f.size)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
