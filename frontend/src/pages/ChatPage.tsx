import { useCallback, useEffect, useRef, useState } from "react"
import type { FormEvent } from "react"
import { MessageSquarePlusIcon, Trash2Icon } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import {
  api,
  type ChatMessage,
  type ChatMessageListResponse,
  type ChatThread,
  type ChatThreadListResponse,
  type ChatTurnResponse,
} from "@/lib/api"
import { cn } from "@/lib/utils"

export function ChatPage() {
  const [threads, setThreads] = useState<ChatThread[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState("")
  const [loadingThreads, setLoadingThreads] = useState(true)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement | null>(null)

  const loadThreads = useCallback(async () => {
    setError(null)
    setLoadingThreads(true)
    try {
      const res = await api<ChatThreadListResponse>("/chat/threads")
      setThreads(res.items)
      // New-chat-first: keep selection only if still present; never auto-open newest.
      setActiveId((current) => {
        if (current && res.items.some((t) => t.id === current)) {
          return current
        }
        return null
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load chats")
    } finally {
      setLoadingThreads(false)
    }
  }, [])

  const loadMessages = useCallback(async (threadId: string) => {
    setError(null)
    setLoadingMessages(true)
    try {
      const res = await api<ChatMessageListResponse>(
        `/chat/threads/${threadId}/messages`,
      )
      setMessages(res.items)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load messages")
      setMessages([])
    } finally {
      setLoadingMessages(false)
    }
  }, [])

  useEffect(() => {
    void loadThreads()
  }, [loadThreads])

  useEffect(() => {
    if (!activeId) {
      setMessages([])
      return
    }
    void loadMessages(activeId)
  }, [activeId, loadMessages])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, sending])

  async function handleNewChat() {
    setError(null)
    try {
      const thread = await api<ChatThread>("/chat/threads", {
        method: "POST",
        body: JSON.stringify({}),
      })
      setThreads((prev) => [thread, ...prev])
      setActiveId(thread.id)
      setMessages([])
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create chat")
    }
  }

  async function handleDeleteThread(threadId: string) {
    setError(null)
    try {
      await api<void>(`/chat/threads/${threadId}`, { method: "DELETE" })
      setThreads((prev) => prev.filter((t) => t.id !== threadId))
      if (activeId === threadId) {
        setActiveId(null)
        setMessages([])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete chat")
    }
  }

  async function handleSend(e: FormEvent) {
    e.preventDefault()
    const content = draft.trim()
    if (!content || sending) {
      return
    }

    setError(null)
    setSending(true)
    try {
      let threadId = activeId
      if (!threadId) {
        const thread = await api<ChatThread>("/chat/threads", {
          method: "POST",
          body: JSON.stringify({}),
        })
        setThreads((prev) => [thread, ...prev])
        threadId = thread.id
        setActiveId(thread.id)
      }

      const optimistic: ChatMessage = {
        id: `local-${Date.now()}`,
        thread_id: threadId,
        role: "user",
        content,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, optimistic])
      setDraft("")

      const turn = await api<ChatTurnResponse>(
        `/chat/threads/${threadId}/messages`,
        {
          method: "POST",
          body: JSON.stringify({ content }),
        },
      )
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== optimistic.id),
        turn.user_message,
        turn.assistant_message,
      ])
      setThreads((prev) => {
        const updated = prev.map((t) =>
          t.id === threadId
            ? {
                ...t,
                title:
                  t.title === "New chat"
                    ? content.slice(0, 80)
                    : t.title,
                updated_at: turn.assistant_message.created_at,
              }
            : t,
        )
        return [...updated].sort((a, b) =>
          a.updated_at < b.updated_at ? 1 : -1,
        )
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send message")
      setMessages((prev) => prev.filter((m) => !m.id.startsWith("local-")))
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="flex min-h-[calc(100svh-5.5rem)] flex-col gap-4 py-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Chat</h1>
        <p className="text-sm text-muted-foreground">
          Conversational search with context, powered by LangGraph and
          gpt-4o-mini.
        </p>
      </div>

      {error ? (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}

      <div className="grid min-h-0 flex-1 gap-4 md:grid-cols-[16rem_minmax(0,1fr)]">
        <aside className="flex min-h-0 flex-col gap-2 rounded-xl border bg-card p-3">
          <Button
            type="button"
            variant="outline"
            className="w-full justify-start"
            onClick={() => void handleNewChat()}
          >
            <MessageSquarePlusIcon />
            New chat
          </Button>
          <div className="min-h-0 flex-1 space-y-1 overflow-y-auto">
            {loadingThreads ? (
              <>
                <Skeleton className="h-9 w-full" />
                <Skeleton className="h-9 w-full" />
              </>
            ) : threads.length === 0 ? (
              <p className="px-1 py-2 text-xs text-muted-foreground">
                No chats yet. Start one below.
              </p>
            ) : (
              threads.map((thread) => (
                <div
                  key={thread.id}
                  className={cn(
                    "group flex items-center gap-1 rounded-lg",
                    activeId === thread.id && "bg-muted",
                  )}
                >
                  <button
                    type="button"
                    className="min-w-0 flex-1 truncate px-2 py-2 text-left text-sm hover:bg-muted/80 rounded-lg"
                    onClick={() => setActiveId(thread.id)}
                  >
                    {thread.title}
                  </button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-xs"
                    className="opacity-0 group-hover:opacity-100"
                    aria-label={`Delete ${thread.title}`}
                    onClick={() => void handleDeleteThread(thread.id)}
                  >
                    <Trash2Icon />
                  </Button>
                </div>
              ))
            )}
          </div>
        </aside>

        <section className="flex min-h-0 flex-col rounded-xl border bg-card">
          <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
            {loadingMessages ? (
              <div className="space-y-3">
                <Skeleton className="h-16 w-2/3" />
                <Skeleton className="ml-auto h-16 w-1/2" />
              </div>
            ) : messages.length === 0 ? (
              <div className="flex h-full min-h-48 items-center justify-center text-sm text-muted-foreground">
                {activeId
                  ? "Ask anything. Follow-ups keep prior messages in context."
                  : "Start a new chat below, or open a saved thread from the list."}
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={cn(
                    "max-w-[85%] rounded-2xl px-3 py-2 text-sm",
                    message.role === "user"
                      ? "ml-auto bg-primary text-primary-foreground"
                      : "mr-auto space-y-2 bg-muted text-foreground",
                  )}
                >
                  {message.role === "assistant" && message.thinking ? (
                    <details className="rounded-lg border border-border/60 bg-background/60 px-2 py-1.5 text-muted-foreground">
                      <summary className="cursor-pointer select-none text-xs font-medium text-foreground">
                        Thinking
                      </summary>
                      <p className="mt-1 whitespace-pre-wrap text-xs leading-relaxed">
                        {message.thinking}
                      </p>
                    </details>
                  ) : null}
                  <div className="whitespace-pre-wrap">{message.content}</div>
                </div>
              ))
            )}
            {sending ? (
              <p className="text-xs text-muted-foreground">Thinking…</p>
            ) : null}
            <div ref={bottomRef} />
          </div>

          <form
            onSubmit={(e) => void handleSend(e)}
            className="flex gap-2 border-t p-3"
          >
            <Input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Message…"
              disabled={sending}
              aria-label="Chat message"
            />
            <Button type="submit" disabled={sending || !draft.trim()}>
              Send
            </Button>
          </form>
        </section>
      </div>
    </div>
  )
}
