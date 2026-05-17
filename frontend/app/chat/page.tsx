"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  Send,
  Plus,
  Search,
  Settings,
  ChevronDown,
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
  User,
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
    messages: [],
  },
  {
    id: "3",
    title: "API Design Best Practices",
    lastMessage: "RESTful vs GraphQL comparison",
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24),
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
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [activeChat?.messages, streamingContent]);

  // Auto-resize textarea
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
      await new Promise((resolve) => setTimeout(resolve, 30 + Math.random() * 20));
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

    // Simulate thinking delay
    await new Promise((resolve) => setTimeout(resolve, 800));

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

  const filteredChats = chats.filter(
    (chat) =>
      chat.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      chat.lastMessage.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatTime = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days === 1) return "Yesterday";
    return `${days}d ago`;
  };

  const currentModel = models.find((m) => m.id === selectedModel);

  return (
    <div className="h-screen flex bg-background overflow-hidden">
      {/* Sidebar */}
      <AnimatePresence mode="wait">
        {sidebarOpen && (
          <motion.aside
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 280, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            className="h-full border-r border-border/50 bg-sidebar flex flex-col"
          >
            {/* Sidebar Header */}
            <div className="p-3 flex flex-col gap-2">
              <div className="flex items-center justify-between h-10">
                <Link href="/" className="flex items-center gap-2.5 px-1">
                  <div className="size-7 rounded-lg bg-gradient-to-br from-primary to-primary/60 flex items-center justify-center">
                    <Sparkles className="size-4 text-primary-foreground" />
                  </div>
                  <span className="text-base font-semibold tracking-tight">Omni AI</span>
                </Link>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-8 text-muted-foreground hover:text-foreground"
                      onClick={() => setSidebarOpen(false)}
                    >
                      <PanelLeftClose className="size-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="right">Close sidebar</TooltipContent>
                </Tooltip>
              </div>

              <Button 
                onClick={handleNewChat} 
                className="w-full justify-start gap-2 h-9 text-sm font-medium"
              >
                <Plus data-icon="inline-start" />
                New Chat
              </Button>
            </div>

            <div className="px-3 pb-2">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                <Input
                  placeholder="Search chats..."
                  className="pl-8 h-8 text-sm bg-sidebar-accent/50"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>

            <Separator className="opacity-50" />

            {/* Chat List */}
            <ScrollArea className="flex-1">
              <div className="p-2">
                <p className="px-2 py-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Recent
                </p>
                <div className="flex flex-col gap-0.5">
                  {filteredChats.map((chat) => (
                    <div
                      key={chat.id}
                      className={`group flex items-center gap-2 px-2 py-2 rounded-lg cursor-pointer transition-all duration-150 ${
                        activeChat?.id === chat.id
                          ? "bg-sidebar-accent text-sidebar-accent-foreground"
                          : "hover:bg-sidebar-accent/50 text-muted-foreground hover:text-foreground"
                      }`}
                      onClick={() => setActiveChat(chat)}
                    >
                      <MessageSquare className="size-4 shrink-0 opacity-60" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{chat.title}</p>
                      </div>
                      <span className="text-[10px] text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
                        {formatTime(chat.timestamp)}
                      </span>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="size-6 opacity-0 group-hover:opacity-100 transition-opacity"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <MoreHorizontal className="size-3.5" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-40">
                          <DropdownMenuGroup>
                            <DropdownMenuItem>
                              <Edit2 data-icon="inline-start" />
                              Rename
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                              <Share data-icon="inline-start" />
                              Share
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                              <Bookmark data-icon="inline-start" />
                              Save
                            </DropdownMenuItem>
                          </DropdownMenuGroup>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-destructive focus:text-destructive"
                            onClick={() => handleDeleteChat(chat.id)}
                          >
                            <Trash2 data-icon="inline-start" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  ))}
                </div>
              </div>
            </ScrollArea>

            {/* Sidebar Footer */}
            <div className="p-2 border-t border-border/50">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button 
                    variant="ghost" 
                    className="w-full justify-start gap-2.5 h-12 px-2 hover:bg-sidebar-accent"
                  >
                    <Avatar className="size-8">
                      <AvatarFallback className="bg-gradient-to-br from-primary/30 to-primary/10 text-primary text-sm font-medium">
                        JD
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 text-left min-w-0">
                      <p className="text-sm font-medium truncate">John Doe</p>
                      <p className="text-xs text-muted-foreground">Pro Plan</p>
                    </div>
                    <ChevronDown className="size-4 text-muted-foreground shrink-0" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" className="w-56">
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
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Bar */}
        <header className="h-12 border-b border-border/50 flex items-center justify-between px-3 bg-background/95 backdrop-blur-sm sticky top-0 z-10">
          <div className="flex items-center gap-2">
            {!sidebarOpen && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-8"
                    onClick={() => setSidebarOpen(true)}
                  >
                    <PanelLeft className="size-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="right">Open sidebar</TooltipContent>
              </Tooltip>
            )}

            <Select value={selectedModel} onValueChange={setSelectedModel}>
              <SelectTrigger className="w-[160px] h-8 text-sm border-0 bg-muted/50 hover:bg-muted">
                <div className="flex items-center gap-2">
                  {currentModel && <currentModel.icon className="size-3.5 text-muted-foreground" />}
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
                          <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                            {model.badge}
                          </Badge>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>

            <Badge 
              variant="outline" 
              className="text-[10px] h-6 px-2 gap-1 bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
            >
              <Globe className="size-3" />
              Pro Search
            </Badge>
          </div>

          <div className="flex items-center gap-1">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" className="size-8">
                  <Share className="size-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Share</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" className="size-8" asChild>
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
          <div className="max-w-3xl mx-auto px-4 py-8">
            {activeChat?.messages.length === 0 && !isStreaming ? (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
                className="text-center py-16"
              >
                <motion.div 
                  className="size-16 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center mx-auto mb-8"
                  animate={{ 
                    boxShadow: ["0 0 0 0 rgba(var(--primary), 0)", "0 0 0 12px rgba(var(--primary), 0.1)", "0 0 0 0 rgba(var(--primary), 0)"] 
                  }}
                  transition={{ duration: 2, repeat: Infinity }}
                >
                  <Sparkles className="size-8 text-primary" />
                </motion.div>
                <h2 className="text-2xl font-semibold mb-3 text-balance">
                  What can I help you with?
                </h2>
                <p className="text-muted-foreground mb-10 max-w-md mx-auto text-balance">
                  Ask me anything. I can help with coding, writing, analysis, and much more.
                </p>
                <div className="grid grid-cols-2 gap-2.5 max-w-lg mx-auto">
                  {[
                    { icon: Code2, text: "Write a React component", desc: "Get help with code" },
                    { icon: FileText, text: "Summarize a document", desc: "Extract key points" },
                    { icon: Brain, text: "Explain a concept", desc: "Learn something new" },
                    { icon: ImageIcon, text: "Analyze an image", desc: "Describe visuals" },
                  ].map((item) => (
                    <motion.button
                      key={item.text}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      className="flex flex-col items-start gap-1 p-4 rounded-xl border border-border/50 bg-card/50 hover:bg-card hover:border-border transition-all text-left group"
                      onClick={() => setInput(item.text)}
                    >
                      <item.icon className="size-5 text-muted-foreground group-hover:text-primary transition-colors" />
                      <span className="text-sm font-medium">{item.text}</span>
                      <span className="text-xs text-muted-foreground">{item.desc}</span>
                    </motion.button>
                  ))}
                </div>
              </motion.div>
            ) : (
              <div className="flex flex-col gap-8">
                {activeChat?.messages.map((message, index) => (
                  <motion.div
                    key={message.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.03, duration: 0.3 }}
                  >
                    {message.role === "user" ? (
                      /* User Message - Right aligned bubble */
                      <div className="flex justify-end">
                        <div className="max-w-[85%] flex items-start gap-3">
                          <div className="bg-primary text-primary-foreground rounded-2xl rounded-br-md px-4 py-3">
                            <p className="text-sm leading-relaxed whitespace-pre-wrap">
                              {message.content}
                            </p>
                          </div>
                        </div>
                      </div>
                    ) : (
                      /* Assistant Message - Perplexity-style full width */
                      <div className="flex gap-4">
                        <div className="size-8 rounded-lg bg-gradient-to-br from-primary to-chart-2 flex items-center justify-center shrink-0 mt-1">
                          <Sparkles className="size-4 text-primary-foreground" />
                        </div>
                        <div className="flex-1 min-w-0">
                          {/* Sources */}
                          {message.sources && message.sources.length > 0 && (
                            <div className="flex gap-2 mb-4 overflow-x-auto pb-1">
                              {message.sources.map((source, i) => (
                                <a
                                  key={i}
                                  href={source.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-muted/50 hover:bg-muted text-xs text-muted-foreground hover:text-foreground transition-colors shrink-0"
                                >
                                  <Globe className="size-3" />
                                  <span className="truncate max-w-[120px]">{source.title}</span>
                                </a>
                              ))}
                            </div>
                          )}
                          
                          {/* Message Content */}
                          <div className="prose prose-sm dark:prose-invert max-w-none prose-p:leading-relaxed prose-pre:bg-muted prose-pre:border prose-pre:border-border prose-code:text-primary prose-headings:font-semibold prose-h2:text-base prose-h3:text-sm">
                            <div className="whitespace-pre-wrap">{message.content}</div>
                          </div>
                          
                          {/* Message Actions */}
                          <div className="flex items-center gap-1 mt-4 pt-2">
                            <Badge 
                              variant="secondary" 
                              className="text-[10px] font-normal px-2 h-5"
                            >
                              {models.find((m) => m.id === message.model)?.name || "AI"}
                            </Badge>
                            <span className="text-[10px] text-muted-foreground ml-1">
                              {formatTime(message.timestamp)}
                            </span>
                            <div className="flex-1" />
                            <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button variant="ghost" size="icon" className="size-7">
                                    <ThumbsUp className="size-3.5" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>Good response</TooltipContent>
                              </Tooltip>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button variant="ghost" size="icon" className="size-7">
                                    <ThumbsDown className="size-3.5" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>Bad response</TooltipContent>
                              </Tooltip>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="size-7"
                                    onClick={() => handleCopy(message.content, message.id)}
                                  >
                                    {copiedId === message.id ? (
                                      <Check className="size-3.5 text-emerald-500" />
                                    ) : (
                                      <Copy className="size-3.5" />
                                    )}
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>Copy</TooltipContent>
                              </Tooltip>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button variant="ghost" size="icon" className="size-7">
                                    <RefreshCw className="size-3.5" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>Regenerate</TooltipContent>
                              </Tooltip>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </motion.div>
                ))}

                {/* Streaming Response */}
                {isStreaming && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex gap-4"
                  >
                    <div className="size-8 rounded-lg bg-gradient-to-br from-primary to-chart-2 flex items-center justify-center shrink-0 mt-1">
                      <Sparkles className="size-4 text-primary-foreground" />
                    </div>
                    <div className="flex-1 min-w-0">
                      {streamingContent ? (
                        <div className="prose prose-sm dark:prose-invert max-w-none prose-p:leading-relaxed">
                          <div className="whitespace-pre-wrap">
                            {streamingContent}
                            <motion.span
                              animate={{ opacity: [1, 0] }}
                              transition={{ duration: 0.5, repeat: Infinity, repeatType: "reverse" }}
                              className="inline-block w-2 h-4 ml-0.5 bg-primary rounded-sm align-middle"
                            />
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-center gap-3 py-2">
                          <motion.div
                            className="flex gap-1"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                          >
                            {[0, 1, 2].map((i) => (
                              <motion.span
                                key={i}
                                className="size-2 rounded-full bg-primary/60"
                                animate={{ scale: [1, 1.2, 1], opacity: [0.5, 1, 0.5] }}
                                transition={{
                                  duration: 0.8,
                                  repeat: Infinity,
                                  delay: i * 0.15,
                                }}
                              />
                            ))}
                          </motion.div>
                          <span className="text-sm text-muted-foreground">
                            Thinking...
                          </span>
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
                <div ref={messagesEndRef} className="h-4" />
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Input Area - ChatGPT style */}
        <div className="border-t border-border/50 p-4 bg-gradient-to-t from-background to-background/80">
          <div className="max-w-3xl mx-auto">
            <div className="relative">
              <div className="relative bg-muted/30 border border-border/50 rounded-2xl focus-within:border-primary/30 focus-within:bg-muted/50 transition-all shadow-sm">
                <textarea
                  ref={inputRef}
                  placeholder="Ask anything..."
                  className="w-full min-h-[52px] max-h-[200px] resize-none bg-transparent px-4 py-3.5 pr-24 text-sm placeholder:text-muted-foreground focus:outline-none"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  rows={1}
                />
                <div className="absolute bottom-2 right-2 flex items-center gap-1">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button 
                        variant="ghost" 
                        size="icon" 
                        className="size-8 text-muted-foreground hover:text-foreground"
                      >
                        <Paperclip className="size-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Attach file</TooltipContent>
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button 
                        variant="ghost" 
                        size="icon" 
                        className="size-8 text-muted-foreground hover:text-foreground"
                      >
                        <Mic className="size-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Voice input</TooltipContent>
                  </Tooltip>
                  <Button
                    size="icon"
                    className="size-8 rounded-lg"
                    onClick={handleSend}
                    disabled={!input.trim() || isStreaming}
                  >
                    <ArrowUp className="size-4" />
                  </Button>
                </div>
              </div>
            </div>
            <p className="text-[11px] text-muted-foreground text-center mt-2.5">
              Omni AI may produce inaccurate information. Verify important facts.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
