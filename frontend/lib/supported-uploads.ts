export const ALLOWED_UPLOAD_EXTENSIONS = [
  ".pdf",
  ".txt",
  ".md",
  ".markdown",
  ".docx",
] as const;

export const SUPPORTED_UPLOADS_LABEL = "PDF, DOCX, TXT, Markdown";

export const UPLOAD_ACCEPT = [
  ...ALLOWED_UPLOAD_EXTENSIONS,
  "application/pdf",
  "text/plain",
  "text/markdown",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
].join(",");

export function isSupportedUploadFilename(filename: string): boolean {
  const lower = filename.toLowerCase();
  return ALLOWED_UPLOAD_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

export function stripUploadExtension(filename: string): string {
  const lower = filename.toLowerCase();
  for (const ext of ALLOWED_UPLOAD_EXTENSIONS) {
    if (lower.endsWith(ext)) {
      return filename.slice(0, -ext.length);
    }
  }
  return filename;
}
