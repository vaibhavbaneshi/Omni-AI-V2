"use client";

import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  Plus,
  Search,
  Settings,
  ChevronDown,
  ChevronRight,
  FileText,
  Code2,
  Image as ImageIcon,
  Paperclip,
  MoreHorizontal,
  Trash2,
  Edit2,
  Copy,
  Check,
  PanelLeftClose,
  PanelLeft,
  LayoutDashboard,
  LogOut,
  Globe,
  Zap,
  Brain,
  RefreshCw,
  ThumbsUp,
  ThumbsDown,
  Share,
  ArrowUp,
  Mic,
  Hash,
  Folder,
  Star,
  Clock,
  Command,
  Database,
  Loader2,
  X,
  File as FileIcon,
  UploadCloud,
  Wrench,
  ShieldCheck,
  BookOpen,
  AlertCircle,
  PenLine,
  BarChart3,
  FlaskConical,
  TerminalSquare,
} from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { sidebarTransition, fadeUpVariant } from "@/lib/motion";
import { clearSession, getInitials, useRequireAuth } from "@/lib/auth";
import {
  ApiError,
  createChatSession,
  getChatSessionMessages,
  listChatSessions,
  updateChatSessionTitle,
  type DocumentRecord,
  type StreamMeta,
  type StreamSource,
} from "@/lib/api";
import { useChatStream } from "@/hooks/useChatStream";
import { isBackendSessionId } from "@/lib/chat-sessions";
import { useDocuments } from "@/hooks/useDocuments";
import { useMemory } from "@/hooks/useMemory";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuGroup,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  SelectGroup,
} from "@/components/ui/select";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

const syntaxTheme = vscDarkPlus as Record<string, CSSProperties>;

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  model?: string;
  sources?: SourceCitation[];
  toolMeta?: StreamMeta;
  status?: "complete" | "error";
};

type SourceCitation = StreamSource & {
  url?: string;
};

type Chat = {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: Date;
  messages: Message[];
  pinned?: boolean;
  folder?: string;
};

const models = [
  { id: "gpt-4", name: "GPT-4 Turbo", provider: "OpenAI", icon: Zap, badge: "Latest" },
  { id: "gpt-3.5", name: "GPT-3.5", provider: "OpenAI", icon: Zap, badge: null },
  { id: "claude-3", name: "Claude 3 Opus", provider: "Anthropic", icon: Brain, badge: "Smart" },
  { id: "gemini-pro", name: "Gemini Pro", provider: "Google", icon: Sparkles, badge: null },
];

const workspaceModes = [
  {
    id: "research",
    name: "Research",
    icon: FlaskConical,
    status: "Web + docs",
  },
  {
    id: "coding",
    name: "Coding",
    icon: TerminalSquare,
    status: "Precise",
  },
  {
    id: "writing",
    name: "Writing",
    icon: PenLine,
    status: "Polished",
  },
  {
    id: "analyst",
    name: "Analyst",
    icon: BarChart3,
    status: "Structured",
  },
] as const;

const SIDEBAR_WIDTH_KEY = "omni-ai-sidebar-width";
const SIDEBAR_MIN_WIDTH = 220;
const SIDEBAR_MAX_WIDTH = 420;
const SIDEBAR_DEFAULT_WIDTH = 260;
const MAX_UPLOAD_BYTES = 15 * 1024 * 1024;

function readSidebarWidth() {
  if (typeof window === "undefined") return SIDEBAR_DEFAULT_WIDTH;
  const stored = Number(window.localStorage.getItem(SIDEBAR_WIDTH_KEY));
  if (!Number.isFinite(stored)) return SIDEBAR_DEFAULT_WIDTH;
  return Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, stored));
}

function readUrlChatId() {
  if (typeof window === "undefined") return null;
  return new URLSearchParams(window.location.search).get("id");
}

function buildOptimisticTitle(message: string) {
  const trimmed = message.trim();
  if (!trimmed) return "New Chat";
  return trimmed.length > 42 ? `${trimmed.slice(0, 42).trim()}…` : trimmed;
}

export default function ChatPage() {
  const { session, ready, authenticated } = useRequireAuth();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sidebarWidth, setSidebarWidth] = useState(readSidebarWidth);
  const [isResizingSidebar, setIsResizingSidebar] = useState(false);
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeChat, setActiveChat] = useState<Chat | null>(null);
  const [sessionsLoaded, setSessionsLoaded] = useState(false);
  const activeChatIdRef = useRef<string | null>(null);
  const [selectedModel, setSelectedModel] = useState("gpt-4");
  const [selectedMode, setSelectedMode] = useState<(typeof workspaceModes)[number]["id"]>("research");
  const [input, setInput] = useState("");
  const {
    isStreaming,
    streamingContent,
    streamingMeta,
    streamStatus,
    streamError,
    setStreamError,
    start: startChatStream,
  } = useChatStream();
  const [searchQuery, setSearchQuery] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [feedbackByMessage, setFeedbackByMessage] = useState<Record<string, "up" | "down">>({});
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const {
    documents,
    collections,
    activeCollectionId,
    setActiveCollectionId,
    status: uploadStatus,
    message: uploadMessage,
    setStatus: setUploadStatus,
    setMessage: setUploadMessage,
    refresh: refreshDocuments,
    upload: uploadWorkspaceDocument,
    remove: removeWorkspaceDocument,
  } = useDocuments(session?.token, activeChat?.id ?? null);
  const { memories, addMemory, removeMemory } = useMemory(session?.token);
  const [isDraggingFile, setIsDraggingFile] = useState(false);
  const [deletingDocument, setDeletingDocument] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [expandedFolders, setExpandedFolders] = useState<string[]>(["Work"]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const shouldStickToBottomRef = useRef(true);

  useEffect(() => {
    const syncSidebar = () => setSidebarOpen(window.innerWidth >= 1024);
    syncSidebar();
    window.addEventListener("resize", syncSidebar);
    return () => window.removeEventListener("resize", syncSidebar);
  }, []);

  useEffect(() => {
    activeChatIdRef.current = activeChat?.id ?? null;
  }, [activeChat?.id]);

  useEffect(() => {
    if (!activeChat) return;
    const nextUrl = `/chat?id=${encodeURIComponent(activeChat.id)}`;
    if (window.location.pathname + window.location.search !== nextUrl) {
      window.history.replaceState(null, "", nextUrl);
    }
  }, [activeChat]);

  useEffect(() => {
    if (!isResizingSidebar) return;

    const handleMouseMove = (event: MouseEvent) => {
      const nextWidth = Math.min(
        SIDEBAR_MAX_WIDTH,
        Math.max(SIDEBAR_MIN_WIDTH, event.clientX)
      );
      setSidebarWidth(nextWidth);
      window.localStorage.setItem(SIDEBAR_WIDTH_KEY, String(nextWidth));
    };

    const handleMouseUp = () => setIsResizingSidebar(false);

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizingSidebar]);

  useEffect(() => {
    if (!activeChat?.id) return;
    setAttachedFile(null);
    setUploadStatus("idle");
    setUploadMessage(null);
    setIsDraggingFile(false);
  }, [activeChat?.id, setUploadMessage, setUploadStatus]);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    if (!shouldStickToBottomRef.current) return;
    messagesEndRef.current?.scrollIntoView({ behavior, block: "end" });
  }, []);

  useEffect(() => {
    scrollToBottom(isStreaming ? "auto" : "smooth");
  }, [activeChat?.messages, isStreaming, scrollToBottom, streamingContent]);

  const handleMessagesScroll = (event: React.UIEvent<HTMLDivElement>) => {
    const target = event.currentTarget;
    const distanceFromBottom = target.scrollHeight - target.scrollTop - target.clientHeight;
    shouldStickToBottomRef.current = distanceFromBottom < 120;
  };

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 200) + "px";
    }
  }, [input]);

  useEffect(() => {
    if (!authenticated || !session?.token) return;

    const urlChatId = readUrlChatId();

    listChatSessions(session.token)
      .then((records) => {
        const nextChats: Chat[] = records.map((record) => ({
          id: String(record.id),
          title: record.title,
          lastMessage: "",
          timestamp: new Date(),
          messages: [],
        }));

        setChats(nextChats);

        if (nextChats.length === 0) {
          setActiveChat(null);
          return;
        }

        const urlMatch = urlChatId
          ? nextChats.find((chat) => chat.id === urlChatId)
          : null;

        setActiveChat((current) => {
          if (urlMatch) return urlMatch;
          if (current && nextChats.some((chat) => chat.id === current.id)) {
            return current;
          }
          return nextChats[0];
        });
      })
      .catch(() => undefined)
      .finally(() => setSessionsLoaded(true));
  }, [authenticated, session?.token]);

  useEffect(() => {
    const chatId = activeChat?.id;
    const numericId = chatId && isBackendSessionId(chatId) ? Number(chatId) : null;

    if (!session?.token || !activeChat || numericId === null || !chatId) return;
    if (activeChat.messages.length > 0) return;

    getChatSessionMessages(numericId, session.token)
      .then((records) => {
        const messages = records.map<Message>((record) => ({
          id: String(record.id),
          role: record.role,
          content: record.content,
          timestamp: record.created_at ? new Date(record.created_at) : new Date(),
          model: record.role === "assistant" ? selectedModel : undefined,
        }));

        setActiveChat((current) =>
          current?.id === chatId ? { ...current, messages } : current
        );
        setChats((prev) =>
          prev.map((chat) => (chat.id === chatId ? { ...chat, messages } : chat))
        );
      })
      .catch(() => undefined);
  }, [activeChat?.id, activeChat?.messages.length, selectedModel, session?.token]);

  const handleSend = async (overrideInput?: string, options?: { appendUser?: boolean; chatOverride?: Chat }) => {
    const messageText = (overrideInput ?? input).trim();
    if (!messageText || isStreaming) return;
    shouldStickToBottomRef.current = true;

    const appendUser = options?.appendUser ?? true;
    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: messageText,
      timestamp: new Date(),
    };

    const currentInput = messageText;
    setInput("");
    setStreamError(null);

    let chatForRequest = options?.chatOverride || activeChat;

    try {
      if (!chatForRequest || !isBackendSessionId(chatForRequest.id)) {
        const created = await createChatSession(currentInput, session?.token, {
          title: "New Chat",
        });
        const createdChat: Chat = {
          id: String(created.id),
          title: buildOptimisticTitle(currentInput),
          lastMessage: currentInput,
          timestamp: new Date(),
          messages: [],
        };

        chatForRequest = createdChat;
        setActiveChat(createdChat);
        setChats((prev) => [createdChat, ...prev.filter((chat) => chat.id !== activeChat?.id)]);
      }

      const updatedChat = {
        ...chatForRequest,
        messages: appendUser ? [...chatForRequest.messages, userMessage] : chatForRequest.messages,
        lastMessage: currentInput,
        timestamp: new Date(),
        title:
          chatForRequest.title === "New Chat"
            ? buildOptimisticTitle(currentInput)
            : chatForRequest.title,
      };

      setActiveChat(updatedChat);
      setChats((prev) => prev.map((c) => (c.id === updatedChat.id ? updatedChat : c)));

      const applyTitleUpdate = (payload: { session_id: number; title: string }) => {
        const chatId = String(payload.session_id);
        const updateTitle = (chat: Chat) =>
          chat.id === chatId ? { ...chat, title: payload.title } : chat;
        setChats((prev) => prev.map(updateTitle));
        setActiveChat((prev) => (prev?.id === chatId ? updateTitle(prev) : prev));
      };

      const streamResult = await startChatStream({
        query: currentInput,
        sessionId: Number(updatedChat.id),
        mode: selectedMode,
        collectionId: isBackendSessionId(updatedChat.id) ? undefined : activeCollectionId,
        token: session?.token,
        onTitle: applyTitleUpdate,
      });

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: streamResult.content,
        timestamp: new Date(),
        model: selectedModel,
        sources: streamResult.sources,
        toolMeta: streamResult.meta || undefined,
        status: "complete",
      };

      const completedChat = {
        ...updatedChat,
        messages: [...updatedChat.messages, aiMessage],
        lastMessage: currentInput,
        timestamp: new Date(),
        title: streamResult.title?.title || updatedChat.title,
      };

      setActiveChat(completedChat);
      setChats((prev) => prev.map((c) => (c.id === completedChat.id ? completedChat : c)));
    } catch (error) {
      const isAuthFailure = error instanceof ApiError && error.status === 401;
      const message =
        error instanceof ApiError
          ? error.message
          : "The response stream failed. Check the backend and try again.";

      if (isAuthFailure) {
        clearSession();
        window.location.assign(
          `/login?error=${encodeURIComponent("Your session expired. Please sign in again.")}`
        );
      }

      setStreamError(message);

      if (chatForRequest) {
        const failedMessage: Message = {
          id: (Date.now() + 2).toString(),
          role: "assistant",
          content: message,
          timestamp: new Date(),
          model: selectedModel,
          status: "error",
        };

        const failedChat = {
          ...chatForRequest,
          messages: [...chatForRequest.messages, ...(appendUser ? [userMessage] : []), failedMessage],
        };

        setActiveChat(failedChat);
        setChats((prev) => prev.map((c) => (c.id === failedChat.id ? failedChat : c)));
      }
    }
  };

  const handleNewChat = () => {
    const newChat: Chat = {
      id: `local-${Date.now()}`,
      title: "New Chat",
      lastMessage: "",
      timestamp: new Date(),
      messages: [],
    };
    setChats([newChat, ...chats]);
    setActiveChat(newChat);
  };

  const handleRenameChat = async (chatId: string) => {
    const chat = chats.find((item) => item.id === chatId);
    const nextTitle = window.prompt("Rename chat", chat?.title || "New Chat")?.trim();
    if (!nextTitle) return;

    const update = (item: Chat) => (item.id === chatId ? { ...item, title: nextTitle } : item);
    setChats((prev) => prev.map(update));
    setActiveChat((prev) => (prev?.id === chatId ? update(prev) : prev));

    if (isBackendSessionId(chatId)) {
      try {
        await updateChatSessionTitle(Number(chatId), nextTitle, session?.token);
      } catch {
        // keep optimistic title
      }
    }
  };

  const handleTogglePin = (chatId: string) => {
    const update = (item: Chat) => (item.id === chatId ? { ...item, pinned: !item.pinned } : item);
    setChats((prev) => prev.map(update));
    setActiveChat((prev) => (prev?.id === chatId ? update(prev) : prev));
  };

  const handleMoveToWork = (chatId: string) => {
    const update = (item: Chat) =>
      item.id === chatId ? { ...item, folder: item.folder === "Work" ? undefined : "Work" } : item;
    setChats((prev) => prev.map(update));
    setActiveChat((prev) => (prev?.id === chatId ? update(prev) : prev));
  };

  const handleDeleteChat = (chatId: string) => {
    const remainingChats = chats.filter((c) => c.id !== chatId);
    setChats(remainingChats);
    if (activeChat?.id === chatId) {
      setActiveChat(remainingChats[0] || null);
    }
  };

  const handleCopy = (content: string, id: string) => {
    navigator.clipboard.writeText(content);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleShare = async () => {
    const url = `${window.location.origin}/chat${activeChat ? `?id=${activeChat.id}` : ""}`;
    if (navigator.share) {
      await navigator.share({ title: activeChat?.title || "Omni AI Chat", url });
      return;
    }

    handleCopy(url, "share-link");
  };

  const handleRegenerate = async () => {
    const lastUserMessage = [...(activeChat?.messages || [])].reverse().find((message) => message.role === "user");
    if (!lastUserMessage || isStreaming) return;
    let trimmedChat = activeChat;
    if (activeChat) {
      const trimmedMessages = [...activeChat.messages];
      while (trimmedMessages.length > 0 && trimmedMessages[trimmedMessages.length - 1].role === "assistant") {
        trimmedMessages.pop();
      }
      const nextTrimmedChat = { ...activeChat, messages: trimmedMessages };
      trimmedChat = nextTrimmedChat;
      setActiveChat(nextTrimmedChat);
      setChats((prev) => prev.map((chat) => chat.id === nextTrimmedChat.id ? nextTrimmedChat : chat));
    }
    await handleSend(lastUserMessage.content, { appendUser: false, chatOverride: trimmedChat || undefined });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleFolder = (folder: string) => {
    setExpandedFolders((prev) =>
      prev.includes(folder) ? prev.filter((f) => f !== folder) : [...prev, folder]
    );
  };

  const filteredChats = chats.filter(
    (chat) =>
      chat.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      chat.lastMessage.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const pinnedChats = filteredChats.filter((c) => c.pinned);
  const folders = [...new Set(filteredChats.filter((c) => c.folder).map((c) => c.folder!))];
  const unfolderedChats = filteredChats.filter((c) => !c.pinned && !c.folder);

  const formatTime = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return "now";
    if (minutes < 60) return `${minutes}m`;
    if (hours < 24) return `${hours}h`;
    if (days === 1) return "1d";
    return `${days}d`;
  };

  const currentModel = models.find((m) => m.id === selectedModel);
  const currentMode = workspaceModes.find((mode) => mode.id === selectedMode) || workspaceModes[0];
  const initials = getInitials(session?.name);
  const displayName = session?.name || "John Doe";

  const handleLogout = () => {
    clearSession();
    window.location.assign("/");
  };

  const handleAttachmentClick = () => {
    fileInputRef.current?.click();
  };

  const ensureBackendChat = async (seedTitle?: string): Promise<Chat> => {
    if (activeChat && isBackendSessionId(activeChat.id)) {
      return activeChat;
    }

    const created = await createChatSession(seedTitle || "New Chat", session?.token, {
      title: "New Chat",
    });
    const createdChat: Chat = {
      id: String(created.id),
      title: created.title || "New Chat",
      lastMessage: "",
      timestamp: new Date(),
      messages: activeChat?.messages || [],
    };
    setActiveChat(createdChat);
    setChats((prev) => [createdChat, ...prev.filter((chat) => chat.id !== activeChat?.id)]);
    return createdChat;
  };

  const processSelectedFile = async (file: File) => {
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setAttachedFile(null);
      setUploadStatus("error");
      setUploadMessage("Only PDF documents are supported.");
      return;
    }

    if (file.size > MAX_UPLOAD_BYTES) {
      setAttachedFile(null);
      setUploadStatus("error");
      setUploadMessage(`File exceeds the ${Math.floor(MAX_UPLOAD_BYTES / (1024 * 1024))}MB limit.`);
      return;
    }

    setAttachedFile(file);
    setUploadStatus("uploading");
    setUploadMessage(null);

    try {
      const chat = await ensureBackendChat(file.name.replace(/\.pdf$/i, ""));
      await uploadWorkspaceDocument(file, { sessionId: Number(chat.id) });
    } catch (error) {
      setUploadStatus("error");
      setUploadMessage(
        error instanceof ApiError
          ? error.message
          : "Upload failed. Check that the backend is running."
      );
    }
  };

  const handleFileSelected = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";

    if (file) {
      await processSelectedFile(file);
    }
  };

  const handleDrop = async (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDraggingFile(false);
    const file = event.dataTransfer.files?.[0];

    if (file) {
      await processSelectedFile(file);
    }
  };

  const handleRemoveAttachment = () => {
    setAttachedFile(null);
    setUploadStatus("idle");
    setUploadMessage(null);
  };

  const handleDeleteDocument = async (filename: string) => {
    setDeletingDocument(filename);

    try {
      await removeWorkspaceDocument(filename);
      await refreshDocuments();
      setUploadStatus("success");
      setUploadMessage(`${filename} removed from knowledge base.`);
    } catch (error) {
      setUploadStatus("error");
      setUploadMessage(error instanceof ApiError ? error.message : "Could not remove document.");
    } finally {
      setDeletingDocument(null);
    }
  };

  const memoryFacts = [
    ...(session?.name ? [session.name] : []),
    ...(documents.length > 0 ? [`${documents.length} document${documents.length === 1 ? "" : "s"}`] : []),
    ...(memories.length > 0 ? [`${memories.length} memor${memories.length === 1 ? "y" : "ies"}`] : []),
    ...(activeChat?.messages.length ? ["conversation context"] : []),
  ];

  if (!ready || !authenticated) {
    return <div className="min-h-dvh bg-background" />;
  }

  return (
    <div className="flex h-dvh min-h-0 bg-background overflow-hidden">
      {/* Linear/Cursor-style Sidebar */}
      <AnimatePresence mode="wait">
        {sidebarOpen && (
          <>
            <motion.button
              aria-label="Close sidebar"
              className="fixed inset-0 z-30 bg-black/50 backdrop-blur-sm lg:hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSidebarOpen(false)}
            />
            <motion.aside
              initial={sidebarTransition.initial}
              animate={sidebarTransition.animate}
              exit={sidebarTransition.exit}
              transition={sidebarTransition.transition}
              style={{ width: sidebarWidth }}
              className="fixed inset-y-0 left-0 z-40 flex h-dvh min-h-0 max-w-[82vw] flex-col border-r border-white/5 bg-[#050505] lg:relative lg:z-auto lg:max-w-none lg:shrink-0"
            >
              {/* Sidebar Header */}
              <div className="h-14 flex items-center justify-between px-4 border-b border-white/5">
                <Link href="/" className="flex items-center gap-2.5">
                  <div className="size-6 rounded-md bg-gradient-to-br from-primary to-chart-2 flex items-center justify-center">
                    <Sparkles className="size-3.5 text-primary-foreground" />
                  </div>
                  <span className="text-[15px] font-semibold tracking-tight">Omni AI</span>
                </Link>
                <div className="flex items-center gap-0.5">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-7 text-muted-foreground/70 hover:text-foreground"
                        onClick={handleNewChat}
                      >
                        <Plus className="size-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side="bottom">New chat</TooltipContent>
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-7 text-muted-foreground/70 hover:text-foreground"
                        onClick={() => setSidebarOpen(false)}
                      >
                        <PanelLeftClose className="size-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side="bottom">Close sidebar</TooltipContent>
                  </Tooltip>
                </div>
              </div>

              {/* Search */}
              <div className="p-3">
                <div className="relative">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground/60" />
                  <Input
                    placeholder="Search..."
                    className="pl-8 h-8 text-[12px] bg-white/[0.02] border-white/5 focus:border-white/10 focus:bg-white/[0.04] placeholder:text-muted-foreground/50 transition-colors shadow-inner"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                  <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-0.5 text-[10px] text-muted-foreground/50">
                    <Command className="size-3" />K
                  </div>
                </div>
              </div>

              {/* Chat List */}
              <ScrollArea className="min-h-0 flex-1 px-2">
                <div className="py-1">
                  {/* Pinned Section */}
                  {pinnedChats.length > 0 && (
                    <div className="mb-3">
                      <div className="flex items-center gap-2 px-2 py-1.5">
                        <Star className="size-3 text-muted-foreground/50" />
                        <span className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wide">
                          Pinned
                        </span>
                      </div>
                      <div className="flex flex-col gap-px">
                        {pinnedChats.map((chat) => (
                          <ChatItem
                            key={chat.id}
                            chat={chat}
                            active={activeChat?.id === chat.id}
                            onClick={() => setActiveChat(chat)}
                            onDelete={() => handleDeleteChat(chat.id)}
                            onRename={() => handleRenameChat(chat.id)}
                            onTogglePin={() => handleTogglePin(chat.id)}
                            onMoveToWork={() => handleMoveToWork(chat.id)}
                            formatTime={formatTime}
                          />
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Folders */}
                  {folders.map((folder) => (
                    <div key={folder} className="mb-2">
                      <button
                        className="group flex items-center gap-2 px-2 py-1 w-full hover:bg-white/5 rounded-md transition-colors"
                        onClick={() => toggleFolder(folder)}
                      >
                        <ChevronRight
                          className={`size-3 text-muted-foreground/50 transition-transform ${expandedFolders.includes(folder) ? "rotate-90" : ""
                            }`}
                        />
                        <Folder className="size-3 text-muted-foreground/50" />
                        <span className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wide">
                          {folder}
                        </span>
                        <span className="ml-auto text-[10px] text-muted-foreground/40">
                          {filteredChats.filter((c) => c.folder === folder).length}
                        </span>
                      </button>
                      {expandedFolders.includes(folder) && (
                        <div className="flex flex-col gap-px mt-1 ml-2">
                          {filteredChats
                            .filter((c) => c.folder === folder)
                            .map((chat) => (
                              <ChatItem
                                key={chat.id}
                                chat={chat}
                                active={activeChat?.id === chat.id}
                                onClick={() => setActiveChat(chat)}
                                onDelete={() => handleDeleteChat(chat.id)}
                                onRename={() => handleRenameChat(chat.id)}
                                onTogglePin={() => handleTogglePin(chat.id)}
                                onMoveToWork={() => handleMoveToWork(chat.id)}
                                formatTime={formatTime}
                              />
                            ))}
                        </div>
                      )}
                    </div>
                  ))}

                  {/* Recent / Unfoldered */}
                  {unfolderedChats.length > 0 && (
                    <div className="mb-3">
                      <div className="flex items-center gap-2 px-2 py-1.5">
                        <Clock className="size-3 text-muted-foreground/50" />
                        <span className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wide">
                          Recent
                        </span>
                      </div>
                      <div className="flex flex-col gap-px">
                        {unfolderedChats.map((chat) => (
                          <ChatItem
                            key={chat.id}
                            chat={chat}
                            active={activeChat?.id === chat.id}
                            onClick={() => setActiveChat(chat)}
                            onDelete={() => handleDeleteChat(chat.id)}
                            onRename={() => handleRenameChat(chat.id)}
                            onTogglePin={() => handleTogglePin(chat.id)}
                            onMoveToWork={() => handleMoveToWork(chat.id)}
                            formatTime={formatTime}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </ScrollArea>

              {/* Sidebar Footer */}
              <div className="p-2 border-t border-white/5">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button className="w-full flex items-center gap-2.5 px-2 py-1.5 rounded-lg hover:bg-white/5 transition-colors group">
                      <Avatar className="size-6 ring-1 ring-white/10">
                        <AvatarFallback className="bg-gradient-to-br from-primary/20 to-chart-2/20 text-[10px] font-medium text-foreground">
                          {initials}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1 text-left min-w-0">
                        <p className="text-[12px] font-medium truncate leading-tight group-hover:text-foreground transition-colors text-muted-foreground">{displayName}</p>
                        <p className="text-[10px] text-muted-foreground/50 truncate">Pro Plan</p>
                      </div>
                      <ChevronDown className="size-3.5 text-muted-foreground/40 shrink-0 group-hover:text-muted-foreground/80 transition-colors" />
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start" className="w-52">
                    <DropdownMenuGroup>
                      <DropdownMenuItem asChild>
                        <Link href="/dashboard">
                          <LayoutDashboard data-icon="inline-start" />
                          Dashboard
                        </Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem asChild>
                        <Link href="/settings">
                          <Settings data-icon="inline-start" />
                          Settings
                        </Link>
                      </DropdownMenuItem>
                    </DropdownMenuGroup>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={handleLogout}>
                      <LogOut data-icon="inline-start" />
                      Sign Out
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </motion.aside>
            <div
              role="separator"
              aria-orientation="vertical"
              aria-label="Resize sidebar"
              onMouseDown={() => setIsResizingSidebar(true)}
              className={`hidden lg:block fixed top-0 z-50 h-full w-1 cursor-col-resize transition-colors hover:bg-primary/40 ${
                isResizingSidebar ? "bg-primary/50" : "bg-transparent"
              }`}
              style={{ left: sidebarWidth - 2 }}
            />
          </>
        )}
      </AnimatePresence>

      {/* Main Chat Area */}
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-gradient-to-b from-background to-[oklch(0.09_0.005_285)]">
        {/* Top Bar */}
        <header className="h-14 shrink-0 border-b border-border/40 flex items-center justify-between gap-2 px-3 sm:px-4 bg-background/80 backdrop-blur-md sticky top-0 z-10">
          <div className="flex min-w-0 items-center gap-2 sm:gap-3">
            {!sidebarOpen && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-8 text-muted-foreground hover:text-foreground"
                    onClick={() => setSidebarOpen(true)}
                  >
                    <PanelLeft className="size-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="right">Open sidebar</TooltipContent>
              </Tooltip>
            )}

            <Select value={selectedModel} onValueChange={(value) => value && setSelectedModel(value)}>
              <SelectTrigger className="h-8 max-w-[46vw] gap-2 overflow-hidden border-0 bg-transparent px-2 text-[13px] font-medium hover:bg-muted/50 sm:max-w-none">
                <div className="flex items-center gap-2">
                  {currentModel && <currentModel.icon className="size-3.5 text-primary" />}
                  <SelectValue />
                </div>
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  {models.map((model) => (
                    <SelectItem key={model.id} value={model.id}>
                      <div className="flex items-center gap-2">
                        <model.icon className="size-4 text-muted-foreground" />
                        <span>{model.name}</span>
                        {model.badge && (
                          <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4 font-normal">
                            {model.badge}
                          </Badge>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>

            <div className="hidden items-center gap-1 rounded-lg border border-white/5 bg-white/[0.02] p-1 md:flex">
              {workspaceModes.map((mode) => (
                <Tooltip key={mode.id}>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      className={`flex h-7 items-center gap-1.5 rounded-md px-2 text-[11px] font-medium transition-colors ${selectedMode === mode.id
                          ? "bg-primary/15 text-foreground"
                          : "text-muted-foreground/65 hover:bg-white/[0.04] hover:text-foreground"
                        }`}
                      onClick={() => setSelectedMode(mode.id)}
                    >
                      <mode.icon className="size-3.5" />
                      <span>{mode.name}</span>
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>{mode.status}</TooltipContent>
                </Tooltip>
              ))}
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-1">
            <Badge
              variant="outline"
              className="hidden h-6 gap-1.5 bg-success/5 px-2.5 text-[10px] font-normal text-success border-success/20 sm:inline-flex"
            >
              <span className="size-1.5 rounded-full bg-success animate-pulse" />
              Pro Search
            </Badge>
            <Badge
              variant="outline"
              className="hidden h-6 gap-1.5 border-white/10 bg-white/[0.02] px-2.5 text-[10px] font-normal text-muted-foreground md:inline-flex"
            >
              <currentMode.icon className="size-3 text-primary" />
              {currentMode.name} Mode
            </Badge>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" className="size-8 text-muted-foreground hover:text-foreground" onClick={handleShare}>
                  <Share className="size-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Share</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" className="size-8 text-muted-foreground hover:text-foreground" asChild>
                  <Link href="/settings">
                    <Settings className="size-4" />
                  </Link>
                </Button>
              </TooltipTrigger>
              <TooltipContent>Settings</TooltipContent>
            </Tooltip>
          </div>
        </header>

        {/* Messages Area */}
        <div className="min-h-0 flex-1 overflow-y-auto scrollbar-thin" onScroll={handleMessagesScroll}>
          <div className="mx-auto max-w-[720px] px-4 py-8 sm:px-6 sm:py-10">
            {activeChat?.messages.length === 0 && !isStreaming ? (
              <motion.div
                variants={fadeUpVariant}
                initial="initial"
                animate="animate"
                className="text-center pt-20 pb-16"
              >
                <motion.div
                  className="size-14 rounded-2xl bg-gradient-to-br from-primary/15 to-chart-2/15 flex items-center justify-center mx-auto mb-8 ring-1 ring-primary/10"
                  animate={{
                    scale: [1, 1.02, 1],
                  }}
                  transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
                >
                  <Sparkles className="size-7 text-primary" />
                </motion.div>
                <h1 className="text-[28px] font-semibold tracking-tight mb-3 text-balance">
                  How can I help you today?
                </h1>
                <p className="text-[15px] text-muted-foreground mb-12 max-w-md mx-auto leading-relaxed text-balance">
                  Ask anything. I can help with code, writing, analysis, math, and much more.
                </p>
                <div className="mx-auto grid max-w-lg grid-cols-1 gap-3 sm:grid-cols-2">
                  {[
                    { icon: Code2, text: "Help me write code", color: "from-blue-500/10 to-cyan-500/10" },
                    { icon: FileText, text: "Summarize content", color: "from-amber-500/10 to-orange-500/10" },
                    { icon: Brain, text: "Explain a concept", color: "from-violet-500/10 to-purple-500/10" },
                    { icon: ImageIcon, text: "Analyze an image", color: "from-pink-500/10 to-rose-500/10" },
                  ].map((item) => (
                    <motion.button
                      key={item.text}
                      whileHover={{ scale: 1.01, y: -1 }}
                      whileTap={{ scale: 0.99 }}
                      className={`flex items-center gap-3 p-4 rounded-xl bg-gradient-to-br ${item.color} border border-border/30 hover:border-border/60 transition-all text-left group`}
                      onClick={() => setInput(item.text)}
                    >
                      <div className="size-9 rounded-lg bg-background/80 flex items-center justify-center ring-1 ring-border/50">
                        <item.icon className="size-4 text-muted-foreground group-hover:text-foreground transition-colors" />
                      </div>
                      <span className="text-[13px] font-medium">{item.text}</span>
                    </motion.button>
                  ))}
                </div>
              </motion.div>
            ) : (
              <div className="flex flex-col gap-10">
                {activeChat?.messages.map((message, index) => (
                  <motion.div
                    key={message.id}
                    variants={fadeUpVariant}
                    initial="initial"
                    animate="animate"
                    transition={{ ...fadeUpVariant.transition, delay: index * 0.02 }}
                  >
                    {message.role === "user" ? (
                      <div className="flex justify-end">
                        <div className="max-w-[92%] sm:max-w-[80%]">
                          <div className="bg-primary/10 text-foreground border border-primary/20 rounded-2xl rounded-br-sm px-5 py-3.5 shadow-sm">
                            <p className="text-[15px] leading-relaxed whitespace-pre-wrap">
                              {message.content}
                            </p>
                          </div>
                          <p className="text-[11px] text-muted-foreground/50 mt-1.5 text-right pr-1">
                            {formatTime(message.timestamp)}
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div className="group">
                        <ToolVisibility meta={message.toolMeta} memoryFacts={memoryFacts} />
                        <SourcesPanel sources={message.sources || []} />

                        {/* Message Content */}
                        <div className="prose prose-sm dark:prose-invert max-w-none prose-p:leading-[1.7] prose-p:text-[15px] prose-pre:p-0 prose-pre:bg-transparent prose-pre:border-0 prose-pre:shadow-none prose-pre:m-0 prose-code:text-primary prose-code:font-normal prose-code:bg-primary/10 prose-code:px-1 prose-code:py-0.5 prose-code:rounded-md prose-headings:font-semibold prose-headings:tracking-tight prose-h2:text-[18px] prose-h2:mt-6 prose-h2:mb-4 prose-h3:text-[15px] prose-h3:mt-5 prose-h3:mb-2 prose-ul:my-3 prose-li:my-1 text-foreground/90">
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                              code({ className, children }) {
                                const match = /language-(\w+)/.exec(className || "");
                                return match ? (
                                  <div className="relative mt-4 mb-6 rounded-xl overflow-hidden border border-white/5 shadow-inner bg-[#050505]">
                                    <div className="flex items-center justify-between px-4 py-2 bg-white/[0.02] border-b border-white/5 text-[11px] text-muted-foreground/60 font-medium">
                                      <span>{match[1]}</span>
                                      <button
                                        onClick={() => handleCopy(String(children).replace(/\n$/, ""), message.id)}
                                        className="hover:text-foreground transition-colors flex items-center gap-1.5"
                                      >
                                        {copiedId === message.id ? <Check className="size-3" /> : <Copy className="size-3" />}
                                        {copiedId === message.id ? "Copied" : "Copy"}
                                      </button>
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
                                      {String(children).replace(/\n$/, "")}
                                    </SyntaxHighlighter>
                                  </div>
                                ) : (
                                  <code className={className}>
                                    {children}
                                  </code>
                                );
                              },
                            }}
                          >
                            {message.content}
                          </ReactMarkdown>
                        </div>

                        {/* Message Actions */}
                        <div className="flex items-center gap-2 mt-6 pt-3 border-t border-white/5">
                          <div className="flex items-center gap-2">
                            <div className="size-5 rounded bg-primary/20 flex items-center justify-center border border-primary/30 shadow-[0_0_10px_rgba(var(--primary),0.15)]">
                              <Sparkles className="size-2.5 text-primary" />
                            </div>
                            <span className="text-[11px] text-muted-foreground/60 font-medium">
                              {models.find((m) => m.id === message.model)?.name || "AI"}
                            </span>
                          </div>
                          <span className="text-[11px] text-muted-foreground/40">
                            {formatTime(message.timestamp)}
                          </span>
                          <div className="flex-1" />
                          <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="size-7 text-muted-foreground/60 hover:text-foreground"
                                  onClick={() => setFeedbackByMessage((prev) => ({ ...prev, [message.id]: "up" }))}
                                >
                                  <ThumbsUp className={`size-3.5 ${feedbackByMessage[message.id] === "up" ? "text-success" : ""}`} />
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>Good</TooltipContent>
                            </Tooltip>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="size-7 text-muted-foreground/60 hover:text-foreground"
                                  onClick={() => setFeedbackByMessage((prev) => ({ ...prev, [message.id]: "down" }))}
                                >
                                  <ThumbsDown className={`size-3.5 ${feedbackByMessage[message.id] === "down" ? "text-warning" : ""}`} />
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>Bad</TooltipContent>
                            </Tooltip>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="size-7 text-muted-foreground/60 hover:text-foreground"
                                  onClick={() => handleCopy(message.content, message.id)}
                                >
                                  {copiedId === message.id ? (
                                    <Check className="size-3.5 text-success" />
                                  ) : (
                                    <Copy className="size-3.5" />
                                  )}
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>Copy</TooltipContent>
                            </Tooltip>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button variant="ghost" size="icon" className="size-7 text-muted-foreground/60 hover:text-foreground" onClick={handleRegenerate}>
                                  <RefreshCw className="size-3.5" />
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>Regenerate</TooltipContent>
                            </Tooltip>
                          </div>
                        </div>
                      </div>
                    )}
                  </motion.div>
                ))}

                {/* Streaming Response */}
                {isStreaming && (
                  <motion.div
                    variants={fadeUpVariant}
                    initial="initial"
                    animate="animate"
                    className="group"
                  >
                    <ToolVisibility meta={streamingMeta || undefined} memoryFacts={memoryFacts} live />
                    <SourcesPanel sources={streamingMeta?.sources || []} compact />
                    {streamingContent ? (
                      <div className="prose prose-sm dark:prose-invert max-w-none prose-p:leading-[1.7] prose-p:text-[15px] prose-pre:p-0 prose-pre:bg-transparent prose-pre:border-0 prose-pre:shadow-none prose-pre:m-0 prose-code:text-primary prose-code:font-normal prose-code:bg-primary/10 prose-code:px-1 prose-code:py-0.5 prose-code:rounded-md prose-headings:font-semibold prose-headings:tracking-tight prose-h2:text-[18px] prose-h2:mt-6 prose-h2:mb-4 prose-h3:text-[15px] prose-h3:mt-5 prose-h3:mb-2 prose-ul:my-3 prose-li:my-1 text-foreground/90">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            code({ className, children }) {
                              const match = /language-(\w+)/.exec(className || "");
                              return match ? (
                                <div className="relative mt-4 mb-6 rounded-xl overflow-hidden border border-white/5 shadow-inner bg-[#050505]">
                                  <div className="flex items-center justify-between px-4 py-2 bg-white/[0.02] border-b border-white/5 text-[11px] text-muted-foreground/60 font-medium">
                                    <span>{match[1]}</span>
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
                                    {String(children).replace(/\n$/, "")}
                                  </SyntaxHighlighter>
                                </div>
                              ) : (
                                <code className={className}>
                                  {children}
                                </code>
                              );
                            },
                          }}
                        >
                          {streamingContent + " █"}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <div className="flex flex-wrap items-center gap-3">
                        <div className="size-5 rounded bg-primary/20 flex items-center justify-center border border-primary/30 shadow-[0_0_10px_rgba(var(--primary),0.15)]">
                          <Sparkles className="size-2.5 text-primary" />
                        </div>
                        <div className="flex items-center gap-2">
                          <Loader2 className="size-3.5 animate-spin text-primary" />
                          <span className="text-[13px] font-medium text-foreground/80">
                            {streamStatus?.type === "status" ? streamStatus.message : "Composing response..."}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.02] border border-white/5 shadow-inner ml-2">
                          <Globe className="size-3 text-muted-foreground animate-pulse" />
                          <span className="text-[11px] text-muted-foreground font-medium">Checking workspace context</span>
                        </div>
                      </div>
                    )}
                  </motion.div>
                )}
                {streamError && !isStreaming && (
                  <div className="flex items-center justify-between gap-3 rounded-xl border border-destructive/20 bg-destructive/10 px-3 py-2 text-[12px] text-destructive">
                    <span className="flex items-center gap-2">
                      <AlertCircle className="size-3.5" />
                      {streamError}
                    </span>
                    <Button variant="ghost" size="sm" className="h-7 text-destructive hover:text-destructive" onClick={handleRegenerate}>
                      Retry
                    </Button>
                  </div>
                )}
                <div ref={messagesEndRef} className="h-6" />
              </div>
            )}
          </div>
        </div>

        {/* Input Area */}
        <div className="shrink-0 p-3 pt-2 sm:p-4 sm:pt-2">
          <div className="max-w-[720px] mx-auto">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              className="hidden"
              onChange={handleFileSelected}
            />

            <div className="mb-3 flex gap-1 overflow-x-auto rounded-lg border border-white/5 bg-white/[0.02] p-1 md:hidden">
              {workspaceModes.map((mode) => (
                <button
                  key={mode.id}
                  type="button"
                  className={`flex h-8 shrink-0 items-center gap-1.5 rounded-md px-2.5 text-[11px] font-medium transition-colors ${selectedMode === mode.id
                      ? "bg-primary/15 text-foreground"
                      : "text-muted-foreground/65"
                    }`}
                  onClick={() => setSelectedMode(mode.id)}
                >
                  <mode.icon className="size-3.5" />
                  {mode.name}
                </button>
              ))}
            </div>

            {memories.length > 0 && (
              <div className="mb-3 flex items-center gap-1.5 overflow-x-auto px-1">
                <Brain className="size-3.5 shrink-0 text-primary" />
                {memories.slice(0, 4).map((memory) => (
                  <MemoryChip
                    key={memory.id}
                    label={memory.content}
                    onDelete={() => removeMemory(memory.id)}
                  />
                ))}
              </div>
            )}

            <div
              className={`mb-3 rounded-xl border border-dashed px-3 py-3 transition-all ${isDraggingFile
                  ? "border-primary/50 bg-primary/10"
                  : "border-white/10 bg-white/[0.015]"
                }`}
              onDragOver={(event) => {
                event.preventDefault();
                setIsDraggingFile(true);
              }}
              onDragLeave={() => setIsDraggingFile(false)}
              onDrop={handleDrop}
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <button
                  type="button"
                  className="flex min-w-0 items-center gap-3 text-left"
                  onClick={handleAttachmentClick}
                  disabled={uploadStatus === "uploading"}
                >
                  <div className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-[#050505]">
                    {uploadStatus === "uploading" ? (
                      <Loader2 className="size-4 animate-spin text-primary" />
                    ) : (
                      <UploadCloud className="size-4 text-primary" />
                    )}
                  </div>
                  <div className="min-w-0">
                    <p className="text-[12px] font-medium text-foreground/85">
                      Drop PDFs to attach to this chat
                    </p>
                    <p className="truncate text-[11px] text-muted-foreground/55">
                      {documents.length > 0
                        ? `${documents.length} file${documents.length === 1 ? "" : "s"} in this chat`
                        : "PDFs uploaded here are scoped to this conversation"}
                    </p>
                  </div>
                </button>
                <div className="flex flex-wrap gap-1.5">
                  {documents.slice(0, 3).map((document) => (
                    <DocumentChip
                      key={document.filename}
                      document={document}
                      deleting={deletingDocument === document.filename}
                      onDelete={() => handleDeleteDocument(document.filename)}
                    />
                  ))}
                  {documents.length > 3 && (
                    <span className="rounded-full border border-white/10 bg-white/[0.03] px-2 py-1 text-[10px] text-muted-foreground">
                      +{documents.length - 3}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {(attachedFile || uploadMessage) && (
              <div className="mb-2 space-y-1 px-1">
                {attachedFile && (
                  <motion.div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-[#050505] border border-white/5 shadow-inner group">
                    {uploadStatus === "uploading" ? (
                      <Loader2 className="size-3.5 animate-spin text-primary" />
                    ) : (
                      <FileIcon className="size-3.5 text-blue-400" />
                    )}
                    <span className="text-[11px] font-medium text-foreground/80 truncate max-w-[180px]">
                      {attachedFile.name}
                    </span>
                    <button
                      type="button"
                      className="size-4 rounded-full bg-white/5 flex items-center justify-center opacity-70 hover:opacity-100 hover:bg-white/10 ml-1"
                      onClick={handleRemoveAttachment}
                      aria-label="Remove attachment"
                      disabled={uploadStatus === "uploading"}
                    >
                      <X className="size-2.5 text-muted-foreground hover:text-foreground" />
                    </button>
                  </motion.div>
                )}
                {uploadMessage && (
                  <p
                    className={`text-[11px] ${uploadStatus === "error" ? "text-destructive" : "text-emerald-300"
                      }`}
                  >
                    {uploadMessage}
                  </p>
                )}
              </div>
            )}

            <div className="relative">
              <div className="bg-white/[0.02] backdrop-blur-xl border border-white/5 rounded-2xl focus-within:border-primary/30 focus-within:ring-1 focus-within:ring-primary/10 focus-within:bg-white/[0.04] transition-all shadow-premium">
                <textarea
                  ref={inputRef}
                  placeholder="Message Omni AI..."
                  className="w-full min-h-[56px] max-h-[32dvh] resize-none bg-transparent px-4 py-4 pr-40 text-[15px] placeholder:text-muted-foreground/40 focus:outline-none leading-relaxed sm:px-5"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  rows={1}
                />
                <div className="absolute bottom-3 right-3 flex items-center gap-1">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-8 text-muted-foreground/50 hover:text-foreground hover:bg-muted/50"
                        onClick={() => input.trim() && addMemory(input.trim())}
                        disabled={!input.trim()}
                      >
                        <Brain className="size-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Remember</TooltipContent>
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-8 text-muted-foreground/50 hover:text-foreground hover:bg-muted/50"
                        onClick={handleAttachmentClick}
                        disabled={uploadStatus === "uploading"}
                      >
                        <Paperclip className="size-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Attach</TooltipContent>
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-8 text-muted-foreground/50 hover:text-foreground hover:bg-muted/50"
                        onClick={() => setInput((prev) => prev || "Transcribe this voice note")}
                      >
                        <Mic className="size-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Voice</TooltipContent>
                  </Tooltip>
                  <Button
                    size="icon"
                    className={`size-8 rounded-lg transition-all duration-300 ${input.trim() && !isStreaming ? "glow-primary bg-primary text-primary-foreground hover:bg-primary/90" : "bg-white/5 text-muted-foreground/50"}`}
                    onClick={() => handleSend()}
                    disabled={!input.trim() || isStreaming}
                  >
                    <ArrowUp className="size-4" />
                  </Button>
                </div>
              </div>
            </div>
            <p className="text-[11px] text-muted-foreground/40 text-center mt-3">
              Omni AI may produce inaccurate information. Always verify important facts.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function ToolVisibility({
  meta,
  memoryFacts,
  live = false,
}: {
  meta?: StreamMeta | null;
  memoryFacts: string[];
  live?: boolean;
}) {
  const tool = meta?.tool || "rag";
  const toolLabel =
    tool === "calculator" || meta?.route?.tools?.includes("calculator")
      ? "Calculator"
      : meta?.route?.tools?.includes("web_search")
        ? meta?.route?.tools?.includes("vector_retrieval")
          ? "Web + documents"
          : "Web search"
        : tool === "web_search"
          ? "Web search"
          : "Document search";

  return (
    <div className="mb-4 flex flex-wrap items-center gap-2">
      <div className="flex items-center gap-2 rounded-full border border-white/5 bg-white/[0.02] px-3 py-1.5 text-[11px] font-medium text-muted-foreground/80 shadow-inner">
        {live ? <Loader2 className="size-3.5 animate-spin text-primary" /> : <Wrench className="size-3.5 text-primary" />}
        <span>{live ? "Using" : "Used"} {toolLabel}</span>
      </div>
      {meta?.strategy && (
        <div className="flex items-center gap-2 rounded-full border border-white/5 bg-white/[0.02] px-3 py-1.5 text-[11px] font-medium text-muted-foreground/80 shadow-inner">
          <Database className="size-3.5 text-blue-400" />
          <span>{meta.strategy}</span>
        </div>
      )}
      {meta?.route?.status && (
        <div className="flex items-center gap-2 rounded-full border border-white/5 bg-white/[0.02] px-3 py-1.5 text-[11px] font-medium text-muted-foreground/80 shadow-inner">
          <Search className="size-3.5 text-cyan-300" />
          <span>Search {meta.route.status}</span>
        </div>
      )}
      {meta?.mode && (
        <div className="flex items-center gap-2 rounded-full border border-white/5 bg-white/[0.02] px-3 py-1.5 text-[11px] font-medium text-muted-foreground/80 shadow-inner">
          <Sparkles className="size-3.5 text-violet-300" />
          <span>{meta.mode} mode</span>
        </div>
      )}
      <div className="flex items-center gap-2 rounded-full border border-white/5 bg-white/[0.02] px-3 py-1.5 text-[11px] font-medium text-muted-foreground/80 shadow-inner">
        <ShieldCheck className="size-3.5 text-emerald-300" />
        <span>
          Memory {meta?.memory?.conversation_history || memoryFacts.length > 0 ? "available" : "ready"}
        </span>
      </div>
      {memoryFacts.slice(0, 2).map((fact) => (
        <span
          key={fact}
          className="rounded-full border border-primary/15 bg-primary/5 px-2.5 py-1 text-[10px] font-medium text-primary/90"
        >
          {fact}
        </span>
      ))}
    </div>
  );
}

function SourcesPanel({
  sources,
  compact = false,
}: {
  sources: SourceCitation[];
  compact?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);

  if (sources.length === 0) return null;

  const webSources = sources.filter((source) => source.type === "web");
  const memorySources = sources.filter((source) => source.type === "memory");
  const documentSources = sources.filter((source) => source.type !== "web" && source.type !== "memory");

  return (
    <div className={compact ? "mb-4" : "mb-6"}>
      <div className="mb-2 flex items-center justify-between gap-3">
        <p className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground/60">
          <BookOpen className="size-3" />
          Sources used
          {webSources.length > 0 && (
            <span className="rounded-full bg-cyan-400/10 px-1.5 py-0.5 text-[9px] text-cyan-200">
              {webSources.length} web
            </span>
          )}
          {documentSources.length > 0 && (
            <span className="rounded-full bg-primary/10 px-1.5 py-0.5 text-[9px] text-primary">
              {documentSources.length} docs
            </span>
          )}
          {memorySources.length > 0 && (
            <span className="rounded-full bg-emerald-400/10 px-1.5 py-0.5 text-[9px] text-emerald-200">
              {memorySources.length} memory
            </span>
          )}
        </p>
        <button
          type="button"
          className="text-[11px] font-medium text-muted-foreground/70 transition-colors hover:text-foreground"
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? "Hide chunks" : "View chunks"}
        </button>
      </div>
      <div className="flex gap-2 overflow-x-auto pb-2 -mx-1 px-1 scrollbar-thin">
        {sources.map((source, index) => (
          <SourceCard key={`${source.source}-${index}`} source={source} index={index} />
        ))}
      </div>
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-2 space-y-2">
              {[
                { label: "Workspace documents", items: documentSources },
                { label: "Live web", items: webSources },
                { label: "Memory", items: memorySources },
              ].map((group) => group.items.length > 0 && (
                <div key={group.label} className="space-y-2">
                  <p className="px-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground/45">
                    {group.label}
                  </p>
                  {group.items.map((source, index) => (
                    <div
                      key={`${source.source}-chunk-${index}`}
                      className="rounded-xl border border-white/5 bg-[#050505] p-3 shadow-inner"
                    >
                      <div className="mb-2 flex items-center justify-between gap-3 text-[10px] text-muted-foreground/55">
                        <span className="truncate font-medium">{source.title || source.source}</span>
                        {typeof source.score === "number" && <span>{Math.round(source.score * 100)}% match</span>}
                      </div>
                      <p className="line-clamp-5 text-[12px] leading-relaxed text-muted-foreground/80">
                        {source.chunk}
                      </p>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function SourceCard({
  source,
  index,
}: {
  source: SourceCitation;
  index: number;
}) {
  const body = (
    <div className="group/source flex w-[190px] shrink-0 flex-col justify-between gap-2 rounded-xl border border-white/5 bg-[#050505] px-3 py-2.5 shadow-inner transition-colors hover:bg-white/[0.03]">
      <div className="flex items-center gap-2">
        <div className="flex size-5 shrink-0 items-center justify-center rounded-md bg-white/10">
          {source.type === "web" ? (
            <Globe className="size-3 text-cyan-200 transition-colors group-hover/source:text-foreground" />
          ) : source.type === "memory" ? (
            <Brain className="size-3 text-emerald-200 transition-colors group-hover/source:text-foreground" />
          ) : (
            <FileText className="size-3 text-primary transition-colors group-hover/source:text-foreground" />
          )}
        </div>
        <span className="truncate text-[10px] text-muted-foreground/60">
          {source.source || source.title || `Source ${index + 1}`}
        </span>
      </div>
      <span className="line-clamp-2 text-[12px] font-medium leading-snug text-foreground/85 transition-colors group-hover/source:text-foreground">
        {source.title || source.source || `Retrieved chunk ${index + 1}`}
      </span>
      <div className="flex items-center justify-between text-[10px] text-muted-foreground/45">
        <span>{source.type === "web" ? "live web" : source.type === "memory" ? "memory" : source.strategy || "retrieval"}</span>
        {typeof source.score === "number" && <span>{Math.round(source.score * 100)}%</span>}
      </div>
    </div>
  );

  if (!source.url) return body;

  return (
    <a href={source.url} target="_blank" rel="noopener noreferrer">
      {body}
    </a>
  );
}

function DocumentChip({
  document,
  deleting,
  onDelete,
}: {
  document: DocumentRecord;
  deleting: boolean;
  onDelete: () => void;
}) {
  return (
    <span className="group inline-flex max-w-[180px] items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.03] px-2 py-1 text-[10px] text-muted-foreground">
      <FileIcon className="size-3 shrink-0 text-blue-300" />
      <span className="truncate">{document.filename}</span>
      <button
        type="button"
        className="ml-0.5 flex size-4 shrink-0 items-center justify-center rounded-full hover:bg-white/10 hover:text-foreground"
        onClick={onDelete}
        aria-label={`Remove ${document.filename}`}
        disabled={deleting}
      >
        {deleting ? <Loader2 className="size-2.5 animate-spin" /> : <X className="size-2.5" />}
      </button>
    </span>
  );
}

function MemoryChip({
  label,
  onDelete,
}: {
  label: string;
  onDelete: () => void;
}) {
  return (
    <span className="group inline-flex max-w-[190px] items-center gap-1.5 rounded-full border border-primary/15 bg-primary/5 px-2 py-1 text-[10px] text-primary/90">
      <span className="truncate">{label}</span>
      <button
        type="button"
        className="ml-0.5 flex size-4 shrink-0 items-center justify-center rounded-full hover:bg-white/10 hover:text-foreground"
        onClick={onDelete}
        aria-label="Delete memory"
      >
        <X className="size-2.5" />
      </button>
    </span>
  );
}

function ChatItem({
  chat,
  active,
  onClick,
  onDelete,
  onRename,
  onTogglePin,
  onMoveToWork,
  formatTime,
}: {
  chat: Chat;
  active: boolean;
  onClick: () => void;
  onDelete: () => void;
  onRename: () => void;
  onTogglePin: () => void;
  onMoveToWork: () => void;
  formatTime: (date: Date) => string;
}) {
  return (
    <div
      className={`group relative flex items-center gap-2 px-2 py-1 rounded-md cursor-pointer transition-colors duration-150 ${active
          ? "bg-white/5 text-foreground shadow-[inset_2px_0_0_0_rgba(var(--primary))]"
          : "text-muted-foreground/70 hover:bg-white/[0.03] hover:text-foreground"
        }`}
      onClick={onClick}
    >
      <Hash className={`size-3.5 shrink-0 ${active ? "text-primary" : "opacity-50"}`} />
      <span className="flex-1 text-[12px] truncate font-medium">{chat.title}</span>
      <span className={`text-[10px] ${active ? "text-muted-foreground/60" : "text-muted-foreground/40 opacity-0 group-hover:opacity-100"} transition-opacity`}>
        {formatTime(chat.timestamp)}
      </span>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="size-5 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground/60 hover:text-foreground"
            onClick={(e) => e.stopPropagation()}
          >
            <MoreHorizontal className="size-3" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-36">
          <DropdownMenuGroup>
            <DropdownMenuItem onClick={onRename}>
              <Edit2 data-icon="inline-start" />
              Rename
            </DropdownMenuItem>
            <DropdownMenuItem onClick={onTogglePin}>
              <Star data-icon="inline-start" />
              {chat.pinned ? "Unpin" : "Pin"}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={onMoveToWork}>
              <Folder data-icon="inline-start" />
              {chat.folder === "Work" ? "Remove from Work" : "Move to Work"}
            </DropdownMenuItem>
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            className="text-destructive focus:text-destructive"
            onClick={onDelete}
          >
            <Trash2 data-icon="inline-start" />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
