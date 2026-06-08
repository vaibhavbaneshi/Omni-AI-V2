"use client";

import type { CSSProperties, ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Check, Copy } from "lucide-react";

const syntaxTheme = vscDarkPlus as Record<string, CSSProperties>;

const markdownClassName =
  "prose prose-sm dark:prose-invert max-w-none " +
  "prose-p:leading-[1.7] prose-p:text-[15px] prose-p:my-3 " +
  "prose-pre:p-0 prose-pre:bg-transparent prose-pre:border-0 prose-pre:shadow-none prose-pre:m-0 " +
  "prose-code:text-primary prose-code:font-normal prose-code:bg-primary/10 prose-code:px-1 prose-code:py-0.5 prose-code:rounded-md " +
  "prose-headings:font-semibold prose-headings:tracking-tight prose-headings:text-foreground " +
  "prose-h1:text-[22px] prose-h1:mt-2 prose-h1:mb-4 prose-h1:leading-tight " +
  "prose-h2:text-[18px] prose-h2:mt-6 prose-h2:mb-3 prose-h2:border-b prose-h2:border-white/5 prose-h2:pb-2 " +
  "prose-h3:text-[15px] prose-h3:mt-5 prose-h3:mb-2 " +
  "prose-ul:my-3 prose-ul:pl-5 prose-ol:my-3 prose-ol:pl-5 " +
  "prose-li:my-1.5 prose-li:leading-[1.65] prose-li:marker:text-muted-foreground/70 " +
  "prose-strong:text-foreground prose-strong:font-semibold " +
  "prose-blockquote:border-l-primary/40 prose-blockquote:bg-white/[0.02] prose-blockquote:py-1 prose-blockquote:px-4 prose-blockquote:rounded-r-lg " +
  "prose-table:my-4 prose-th:px-3 prose-th:py-2 prose-td:px-3 prose-td:py-2 " +
  "text-foreground/90";

type MarkdownMessageProps = {
  content: string;
  copiedId?: string | null;
  copyTargetId?: string;
  onCopy?: (content: string, id: string) => void;
  trailing?: ReactNode;
  isStreaming?: boolean;
};

export function MarkdownMessage({
  content,
  copiedId,
  copyTargetId,
  onCopy,
  trailing,
  isStreaming = false,
}: MarkdownMessageProps) {
  if (isStreaming) {
    return (
      <div className={`${markdownClassName} whitespace-pre-wrap`}>
        {content}
        {trailing}
      </div>
    );
  }

  return (
    <div className={markdownClassName}>
      <ReactMarkdown
        skipHtml
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className, children }) {
            const match = /language-(\w+)/.exec(className || "");
            const codeText = String(children).replace(/\n$/, "");

            if (match) {
              return (
                <div className="relative mt-4 mb-6 rounded-xl overflow-hidden border border-white/5 shadow-inner bg-[#050505] not-prose">
                  <div className="flex items-center justify-between px-4 py-2 bg-white/[0.02] border-b border-white/5 text-[11px] text-muted-foreground/60 font-medium">
                    <span>{match[1]}</span>
                    {onCopy && copyTargetId ? (
                      <button
                        type="button"
                        onClick={() => onCopy(codeText, copyTargetId)}
                        className="hover:text-foreground transition-colors flex items-center gap-1.5"
                      >
                        {copiedId === copyTargetId ? (
                          <Check className="size-3" />
                        ) : (
                          <Copy className="size-3" />
                        )}
                        {copiedId === copyTargetId ? "Copied" : "Copy"}
                      </button>
                    ) : null}
                  </div>
                  <SyntaxHighlighter
                    style={syntaxTheme}
                    language={match[1]}
                    PreTag="div"
                    customStyle={{
                      margin: 0,
                      padding: "1rem",
                      background: "transparent",
                      fontSize: "13px",
                    }}
                  >
                    {codeText}
                  </SyntaxHighlighter>
                </div>
              );
            }

            return <code className={className}>{children}</code>;
          },
        }}
      >
        {content}
      </ReactMarkdown>
      {trailing}
    </div>
  );
}
