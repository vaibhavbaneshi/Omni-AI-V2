"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  Plus,
  Search,
  Settings,
  ChevronDown,
  ChevronRight,
  MessageSquare,
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
  Bookmark,
  ArrowUp,
  Mic,
  Hash,
  Folder,
  Star,
  Clock,
  Command,
} from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
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
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [chats, setChats] = useState<Chat[]>(initialChats);
  const [activeChat, setActiveChat] = useState<Chat | null>(initialChats[0]);
  const [selectedModel, setSelectedModel] = useState("gpt-4");
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [expandedFolders, setExpandedFolders] = useState<string[]>(["Work"]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

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

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    const currentInput = input.trim();
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

  const handleDeleteChat = (chatId: string) => {
    setChats(chats.filter((c) => c.id !== chatId));
    if (activeChat?.id === chatId) {
      setActiveChat(chats[0] || null);
    }
  };

  const handleCopy = (content: string, id: string) => {
    navigator.clipboard.writeText(content);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
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

  return (
    <div className="h-screen flex bg-background overflow-hidden">
      {/* Linear/Cursor-style Sidebar */}
      <AnimatePresence mode="wait">
        {sidebarOpen && (
          <motion.aside
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 260, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            className="h-full border-r border-border/40 bg-[oklch(0.095_0.005_285)] flex flex-col"
          >
            {/* Sidebar Header */}
            <div className="h-14 flex items-center justify-between px-4 border-b border-border/40">
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
                  className="pl-8 h-8 text-[13px] bg-background/50 border-border/40 focus:border-border focus:bg-background placeholder:text-muted-foreground/50"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-0.5 text-[10px] text-muted-foreground/50">
                  <Command className="size-3" />K
                </div>
              </div>
            </div>

            {/* Chat List */}
            <ScrollArea className="flex-1 px-2">
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
                      className="flex items-center gap-2 px-2 py-1.5 w-full hover:bg-muted/30 rounded-md transition-colors"
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
                          formatTime={formatTime}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>

            {/* Sidebar Footer */}
            <div className="p-2 border-t border-border/40">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button className="w-full flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-muted/30 transition-colors">
                    <Avatar className="size-7 ring-1 ring-border/50">
                      <AvatarFallback className="bg-gradient-to-br from-primary/20 to-chart-2/20 text-[11px] font-medium">
                        JD
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 text-left min-w-0">
                      <p className="text-[13px] font-medium truncate leading-tight">John Doe</p>
                      <p className="text-[11px] text-muted-foreground/60 truncate">Pro Plan</p>
                    </div>
                    <ChevronDown className="size-3.5 text-muted-foreground/50 shrink-0" />
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
                  <DropdownMenuItem asChild>
                    <Link href="/login">
                      <LogOut data-icon="inline-start" />
                      Sign Out
                    </Link>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0 bg-gradient-to-b from-background to-[oklch(0.09_0.005_285)]">
        {/* Top Bar */}
        <header className="h-14 border-b border-border/40 flex items-center justify-between px-4 bg-background/80 backdrop-blur-md sticky top-0 z-10">
          <div className="flex items-center gap-3">
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

            <Select value={selectedModel} onValueChange={setSelectedModel}>
              <SelectTrigger className="w-auto h-8 gap-2 text-[13px] font-medium border-0 bg-transparent hover:bg-muted/50 px-2">
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

          <div className="flex items-center gap-1">
            <Badge 
              variant="outline" 
              className="text-[10px] h-6 px-2.5 gap-1.5 bg-success/5 text-success border-success/20 font-normal"
            >
              <span className="size-1.5 rounded-full bg-success animate-pulse" />
              Pro Search
            </Badge>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" className="size-8 text-muted-foreground hover:text-foreground">
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
        <ScrollArea className="flex-1">
          <div className="max-w-[720px] mx-auto px-6 py-10">
            {activeChat?.messages.length === 0 && !isStreaming ? (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, ease: "easeOut" }}
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
                <div className="grid grid-cols-2 gap-3 max-w-lg mx-auto">
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
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.02, duration: 0.3 }}
                  >
                    {message.role === "user" ? (
                      <div className="flex justify-end">
                        <div className="max-w-[80%]">
                          <div className="bg-primary text-primary-foreground rounded-2xl rounded-br-md px-4 py-3 shadow-sm">
                            <p className="text-[14px] leading-relaxed whitespace-pre-wrap">
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
                        {/* Sources */}
                        {message.sources && message.sources.length > 0 && (
                          <div className="flex gap-2 mb-4 overflow-x-auto pb-1">
                            {message.sources.map((source, i) => (
                              <a
                                key={i}
                                href={source.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-muted/40 hover:bg-muted text-[12px] text-muted-foreground hover:text-foreground transition-colors shrink-0 ring-1 ring-border/30"
                              >
                                <Globe className="size-3" />
                                <span className="truncate max-w-[140px]">{source.title}</span>
                              </a>
                            ))}
                          </div>
                        )}
                        
                        {/* Message Content */}
                        <div className="prose prose-sm dark:prose-invert max-w-none prose-p:leading-[1.7] prose-p:text-[14px] prose-pre:bg-[oklch(0.12_0.005_285)] prose-pre:border prose-pre:border-border/40 prose-pre:rounded-xl prose-code:text-primary prose-code:font-normal prose-headings:font-semibold prose-h2:text-[16px] prose-h2:mt-6 prose-h2:mb-3 prose-h3:text-[14px] prose-h3:mt-4 prose-h3:mb-2 prose-ul:my-3 prose-li:my-1">
                          <div className="whitespace-pre-wrap text-[14px] leading-[1.7]">{message.content}</div>
                        </div>
                        
                        {/* Message Actions */}
                        <div className="flex items-center gap-2 mt-5 pt-3 border-t border-border/30">
                          <div className="flex items-center gap-1.5">
                            <div className="size-5 rounded bg-gradient-to-br from-primary to-chart-2 flex items-center justify-center">
                              <Sparkles className="size-2.5 text-primary-foreground" />
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
                                <Button variant="ghost" size="icon" className="size-7 text-muted-foreground/60 hover:text-foreground">
                                  <ThumbsUp className="size-3.5" />
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>Good</TooltipContent>
                            </Tooltip>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button variant="ghost" size="icon" className="size-7 text-muted-foreground/60 hover:text-foreground">
                                  <ThumbsDown className="size-3.5" />
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
                                <Button variant="ghost" size="icon" className="size-7 text-muted-foreground/60 hover:text-foreground">
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
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="group"
                  >
                    {streamingContent ? (
                      <div className="prose prose-sm dark:prose-invert max-w-none prose-p:leading-[1.7] prose-p:text-[14px]">
                        <div className="whitespace-pre-wrap text-[14px] leading-[1.7]">
                          {streamingContent}
                          <motion.span
                            animate={{ opacity: [1, 0] }}
                            transition={{ duration: 0.4, repeat: Infinity, repeatType: "reverse" }}
                            className="inline-block w-[3px] h-[18px] ml-0.5 bg-primary rounded-full align-middle"
                          />
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center gap-3">
                        <div className="size-5 rounded bg-gradient-to-br from-primary to-chart-2 flex items-center justify-center">
                          <Sparkles className="size-2.5 text-primary-foreground" />
                        </div>
                        <div className="flex items-center gap-2">
                          <motion.div className="flex gap-1">
                            {[0, 1, 2].map((i) => (
                              <motion.span
                                key={i}
                                className="size-1.5 rounded-full bg-primary"
                                animate={{ opacity: [0.3, 1, 0.3] }}
                                transition={{
                                  duration: 1,
                                  repeat: Infinity,
                                  delay: i * 0.2,
                                }}
                              />
                            ))}
                          </motion.div>
                          <span className="text-[13px] text-muted-foreground">Thinking...</span>
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
        <div className="p-4 pt-2">
          <div className="max-w-[720px] mx-auto">
            <div className="relative">
              <div className="bg-[oklch(0.12_0.005_285)] border border-border/40 rounded-2xl focus-within:border-primary/30 focus-within:ring-1 focus-within:ring-primary/10 transition-all shadow-lg shadow-black/5">
                <textarea
                  ref={inputRef}
                  placeholder="Message Omni AI..."
                  className="w-full min-h-[56px] max-h-[200px] resize-none bg-transparent px-4 py-4 pr-28 text-[14px] placeholder:text-muted-foreground/50 focus:outline-none leading-relaxed"
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
                      >
                        <Mic className="size-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Voice</TooltipContent>
                  </Tooltip>
                  <Button
                    size="icon"
                    className="size-8 rounded-lg bg-primary hover:bg-primary/90 shadow-sm"
                    onClick={handleSend}
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
  formatTime,
}: {
  chat: Chat;
  active: boolean;
  onClick: () => void;
  onDelete: () => void;
  formatTime: (date: Date) => string;
}) {
  return (
    <div
      className={`group flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-all duration-100 ${
        active
          ? "bg-muted/60 text-foreground"
          : "text-muted-foreground/80 hover:bg-muted/30 hover:text-foreground"
      }`}
      onClick={onClick}
    >
      <Hash className="size-3.5 shrink-0 opacity-50" />
      <span className="flex-1 text-[13px] truncate">{chat.title}</span>
      <span className="text-[10px] text-muted-foreground/40 opacity-0 group-hover:opacity-100 transition-opacity">
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
            <DropdownMenuItem>
              <Edit2 data-icon="inline-start" />
              Rename
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Star data-icon="inline-start" />
              Pin
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Folder data-icon="inline-start" />
              Move to...
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
