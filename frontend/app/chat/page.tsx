"use client";

import { useState, useRef, useEffect, type CSSProperties } from "react";
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
} from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { sidebarTransition, fadeUpVariant } from "@/lib/motion";
import { clearSession, getInitials, useRequireAuth } from "@/lib/auth";
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
  sources?: { title: string; url: string }[];
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

const initialChats: Chat[] = [
  {
    id: "1",
    title: "React Performance Optimization",
    lastMessage: "How do I optimize this component?",
    timestamp: new Date(Date.now() - 1000 * 60 * 30),
    pinned: true,
    messages: [
      {
        id: "1-1",
        role: "user",
        content: "How do I optimize this React component for better performance?",
        timestamp: new Date(Date.now() - 1000 * 60 * 35),
      },
      {
        id: "1-2",
        role: "assistant",
        content: `Here are several effective strategies to optimize your React component for better performance:

## 1. Use React.memo() for Pure Components

Wrap components that receive the same props frequently to prevent unnecessary re-renders:

\`\`\`jsx
const MyComponent = React.memo(({ data }) => {
  return <div>{data.name}</div>;
});
\`\`\`

## 2. Implement useMemo() for Expensive Calculations

Cache computed values that don't need to be recalculated on every render:

\`\`\`jsx
const expensiveValue = useMemo(() => {
  return computeExpensiveValue(a, b);
}, [a, b]);
\`\`\`

## 3. Use useCallback() for Function References

Stabilize function references passed to child components:

\`\`\`jsx
const handleClick = useCallback(() => {
  doSomething(id);
}, [id]);
\`\`\`

## 4. Virtualize Long Lists

For lists with many items, use libraries like \`react-window\` or \`@tanstack/react-virtual\` to only render visible items.

Would you like me to show you specific examples for your component?`,
        timestamp: new Date(Date.now() - 1000 * 60 * 34),
        model: "gpt-4",
        sources: [
          { title: "React Documentation - Optimization", url: "https://react.dev/learn" },
          { title: "Web.dev Performance Guide", url: "https://web.dev/performance" },
        ],
      },
    ],
  },
  {
    id: "2",
    title: "Python Data Analysis",
    lastMessage: "Can you help with pandas?",
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2),
    folder: "Work",
    messages: [],
  },
  {
    id: "3",
    title: "API Design Best Practices",
    lastMessage: "RESTful vs GraphQL comparison",
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24),
    folder: "Work",
    messages: [],
  },
  {
    id: "4",
    title: "Machine Learning Basics",
    lastMessage: "What is gradient descent?",
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 48),
    messages: [],
  },
];

export default function ChatPage() {
  const { session, ready, authenticated } = useRequireAuth();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [chats, setChats] = useState<Chat[]>(initialChats);
  const [activeChat, setActiveChat] = useState<Chat | null>(() => {
    if (typeof window === "undefined") return initialChats[0];
    const chatId = new URLSearchParams(window.location.search).get("id");
    return initialChats.find((chat) => chat.id === chatId) || initialChats[0];
  });
  const [selectedModel, setSelectedModel] = useState("gpt-4");
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [feedbackByMessage, setFeedbackByMessage] = useState<Record<string, "up" | "down">>({});
  const [attachmentVisible, setAttachmentVisible] = useState(false);
  const [expandedFolders, setExpandedFolders] = useState<string[]>(["Work"]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const syncSidebar = () => setSidebarOpen(window.innerWidth >= 1024);
    syncSidebar();
    window.addEventListener("resize", syncSidebar);
    return () => window.removeEventListener("resize", syncSidebar);
  }, []);

  useEffect(() => {
    if (!activeChat) return;
    const nextUrl = `/chat?id=${encodeURIComponent(activeChat.id)}`;
    if (window.location.pathname + window.location.search !== nextUrl) {
      window.history.replaceState(null, "", nextUrl);
    }
  }, [activeChat]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [activeChat?.messages, streamingContent]);

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 200) + "px";
    }
  }, [input]);

  const simulateStreaming = async (fullContent: string) => {
    setStreamingContent("");
    const words = fullContent.split(" ");
    
    for (let i = 0; i < words.length; i++) {
      await new Promise((resolve) => setTimeout(resolve, 25 + Math.random() * 15));
      setStreamingContent((prev) => prev + (i === 0 ? "" : " ") + words[i]);
    }
    
    return fullContent;
  };

  const handleSend = async (overrideInput?: string) => {
    const messageText = (overrideInput ?? input).trim();
    if (!messageText || isStreaming) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: messageText,
      timestamp: new Date(),
    };

    const currentInput = messageText;
    setInput("");

    if (activeChat) {
      const updatedChat = {
        ...activeChat,
        messages: [...activeChat.messages, userMessage],
        lastMessage: currentInput,
        timestamp: new Date(),
      };
      setActiveChat(updatedChat);
      setChats(chats.map((c) => (c.id === activeChat.id ? updatedChat : c)));
    }

    setIsStreaming(true);
    await new Promise((resolve) => setTimeout(resolve, 600));

    const responseContent = `Based on your question, here's a comprehensive answer:

## Overview

This is a simulated streaming response that demonstrates the enhanced UX. In a real implementation, this would be streamed from your AI backend using Server-Sent Events or WebSockets.

### Key Points

1. **Real-time streaming** provides immediate feedback to users
2. **Markdown rendering** makes responses readable and well-formatted
3. **Source citations** help users verify information

The response would include proper formatting, code blocks, and other rich content based on the selected model configuration.

\`\`\`typescript
// Example code block
const response = await fetch('/api/chat', {
  method: 'POST',
  body: JSON.stringify({ message, model })
});
\`\`\`

Would you like me to elaborate on any of these points?`;

    const finalContent = await simulateStreaming(responseContent);

    const aiMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: "assistant",
      content: finalContent,
      timestamp: new Date(),
      model: selectedModel,
      sources: [
        { title: "Documentation Reference", url: "https://docs.example.com" },
        { title: "API Guide", url: "https://api.example.com/guide" },
      ],
    };

    if (activeChat) {
      const updatedChat = {
        ...activeChat,
        messages: [...activeChat.messages, userMessage, aiMessage],
      };
      setActiveChat(updatedChat);
      setChats(chats.map((c) => (c.id === activeChat.id ? updatedChat : c)));
    }

    setIsStreaming(false);
    setStreamingContent("");
  };

  const handleNewChat = () => {
    const newChat: Chat = {
      id: Date.now().toString(),
      title: "New Chat",
      lastMessage: "",
      timestamp: new Date(),
      messages: [],
    };
    setChats([newChat, ...chats]);
    setActiveChat(newChat);
  };

  const handleRenameChat = (chatId: string) => {
    const chat = chats.find((item) => item.id === chatId);
    const nextTitle = window.prompt("Rename chat", chat?.title || "New Chat")?.trim();
    if (!nextTitle) return;

    const update = (item: Chat) => (item.id === chatId ? { ...item, title: nextTitle } : item);
    setChats((prev) => prev.map(update));
    setActiveChat((prev) => (prev?.id === chatId ? update(prev) : prev));
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
    await handleSend(lastUserMessage.content);
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
  const initials = getInitials(session?.name);
  const displayName = session?.name || "John Doe";

  const handleLogout = () => {
    clearSession();
    window.location.assign("/login");
  };

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
              className="fixed inset-y-0 left-0 z-40 flex h-dvh min-h-0 w-[min(82vw,280px)] flex-col border-r border-white/5 bg-[#050505] lg:relative lg:z-auto lg:w-[260px] lg:shrink-0"
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
                        className={`size-3 text-muted-foreground/50 transition-transform ${
                          expandedFolders.includes(folder) ? "rotate-90" : ""
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
          </div>

          <div className="flex shrink-0 items-center gap-1">
            <Badge 
              variant="outline" 
              className="hidden h-6 gap-1.5 bg-success/5 px-2.5 text-[10px] font-normal text-success border-success/20 sm:inline-flex"
            >
              <span className="size-1.5 rounded-full bg-success animate-pulse" />
              Pro Search
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
        <ScrollArea className="min-h-0 flex-1">
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
                        {/* Reasoning / Tool Mock */}
                        {index === activeChat.messages.length - 1 && !isStreaming && (
                          <div className="flex items-center gap-3 mb-4">
                            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.02] border border-white/5 shadow-inner text-[11px] text-muted-foreground/80 font-medium cursor-pointer hover:bg-white/[0.04] transition-colors">
                              <Brain className="size-3.5 text-primary" />
                              <span>Thought process</span>
                              <ChevronDown className="size-3 opacity-50 ml-1" />
                            </div>
                            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.02] border border-white/5 shadow-inner text-[11px] text-muted-foreground/80 font-medium cursor-default">
                              <Database className="size-3.5 text-blue-400" />
                              <span>Memory updated</span>
                            </div>
                          </div>
                        )}

                        {/* Sources */}
                        {message.sources && message.sources.length > 0 && (
                          <div className="mb-5">
                            <p className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                              <Globe className="size-3" /> Sources
                            </p>
                            <div className="flex gap-2 overflow-x-auto pb-2 -mx-1 px-1 scrollbar-none">
                              {message.sources.map((source, i) => (
                                <a
                                  key={i}
                                  href={source.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="group/source flex flex-col justify-center gap-1.5 px-3 py-2 w-[160px] rounded-xl bg-[#050505] border border-white/5 shadow-inner hover:bg-white/[0.03] transition-colors shrink-0"
                                >
                                  <div className="flex items-center gap-2">
                                    <div className="size-4 rounded bg-white/10 flex items-center justify-center shrink-0">
                                      <Globe className="size-2.5 text-muted-foreground group-hover/source:text-foreground transition-colors" />
                                    </div>
                                    <span className="text-[10px] text-muted-foreground/60 truncate group-hover/source:text-muted-foreground/80 transition-colors">
                                      {(() => {
                                        try { return new URL(source.url).hostname.replace('www.', ''); }
                                        catch { return source.url; }
                                      })()}
                                    </span>
                                  </div>
                                  <span className="text-[12px] font-medium text-foreground/80 truncate group-hover/source:text-foreground transition-colors">{source.title}</span>
                                </a>
                              ))}
                            </div>
                          </div>
                        )}
                        
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
                      <div className="flex items-center gap-3">
                        <div className="size-5 rounded bg-primary/20 flex items-center justify-center border border-primary/30 shadow-[0_0_10px_rgba(var(--primary),0.15)]">
                          <Sparkles className="size-2.5 text-primary" />
                        </div>
                        <div className="flex items-center gap-2">
                          <Loader2 className="size-3.5 animate-spin text-primary" />
                          <span className="text-[13px] font-medium text-foreground/80">Deep reasoning...</span>
                        </div>
                        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.02] border border-white/5 shadow-inner ml-2">
                          <Globe className="size-3 text-muted-foreground animate-pulse" />
                          <span className="text-[11px] text-muted-foreground font-medium">Searching knowledge base...</span>
                        </div>
                      </div>
                    )}
                  </motion.div>
                )}
                <div ref={messagesEndRef} className="h-6" />
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Input Area */}
        <div className="shrink-0 p-3 pt-2 sm:p-4 sm:pt-2">
          <div className="max-w-[720px] mx-auto">
            {/* Mock Upload State */}
            {attachmentVisible && (
            <div className="flex items-center gap-2 mb-2 px-1">
              <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-[#050505] border border-white/5 shadow-inner group cursor-pointer hover:bg-white/[0.02] transition-colors">
                <FileIcon className="size-3.5 text-blue-400" />
                <span className="text-[11px] font-medium text-foreground/80 truncate max-w-[120px]">architecture_v2.pdf</span>
                <button
                  type="button"
                  className="size-4 rounded-full bg-white/5 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-white/10 ml-1"
                  onClick={() => setAttachmentVisible(false)}
                  aria-label="Remove attachment"
                >
                  <X className="size-2.5 text-muted-foreground hover:text-foreground" />
                </button>
              </div>
            </div>
            )}

            <div className="relative">
              <div className="bg-white/[0.02] backdrop-blur-xl border border-white/5 rounded-2xl focus-within:border-primary/30 focus-within:ring-1 focus-within:ring-primary/10 focus-within:bg-white/[0.04] transition-all shadow-premium">
                <textarea
                  ref={inputRef}
                  placeholder="Message Omni AI..."
                  className="w-full min-h-[56px] max-h-[32dvh] resize-none bg-transparent px-4 py-4 pr-28 text-[15px] placeholder:text-muted-foreground/40 focus:outline-none leading-relaxed sm:px-5 sm:pr-32"
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
                        onClick={() => setAttachmentVisible(true)}
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
      className={`group relative flex items-center gap-2 px-2 py-1 rounded-md cursor-pointer transition-colors duration-150 ${
        active
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
