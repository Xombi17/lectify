import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import { PaperPlaneTilt, ChatCircle, Robot, User } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { chatApi } from "@/lib/api";
import { toast } from "sonner";

const SUGGESTIONS = [
    "Summarize the main idea in 3 sentences",
    "Give me 3 likely exam questions",
    "Explain this lecture like I'm a beginner",
];

export default function DoubtChat({ lectureId, canChat }) {
    const [messages, setMessages] = useState([]);
    const [q, setQ] = useState("");
    const [sending, setSending] = useState(false);
    const scrollRef = useRef(null);

    useEffect(() => {
        if (!lectureId) return;
        chatApi.history(lectureId).then(setMessages).catch(() => {});
    }, [lectureId]);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages, sending]);

    const send = async (text) => {
        const question = (text ?? q).trim();
        if (!question || sending) return;
        if (!canChat) return toast.error("Chat needs a ready transcript");
        setQ("");
        setSending(true);
        // optimistic user message
        const tempId = `tmp-${Date.now()}`;
        setMessages((m) => [
            ...m,
            { id: tempId, role: "user", content: question, created_at: new Date().toISOString() },
        ]);
        try {
            const { user_message, assistant_message } = await chatApi.ask(lectureId, question);
            setMessages((m) =>
                m.filter((x) => x.id !== tempId).concat([user_message, assistant_message])
            );
        } catch (err) {
            setMessages((m) => m.filter((x) => x.id !== tempId));
            toast.error(err?.response?.data?.detail || "Couldn't reach the assistant");
        } finally {
            setSending(false);
        }
    };

    if (!canChat) {
        return (
            <div className="border-2 border-dashed border-border bg-card p-10 text-center">
                <ChatCircle size={32} weight="duotone" className="mx-auto text-muted-foreground" />
                <h3 className="font-display mt-3 text-2xl font-bold tracking-tight">
                    Chat unlocks once processing is done
                </h3>
                <p className="text-sm text-muted-foreground">
                    Come back when the lecture status is <span className="font-mono">ready</span>.
                </p>
            </div>
        );
    }

    return (
        <div className="flex flex-col" data-testid="doubt-chat">
            <div
                ref={scrollRef}
                className="mb-4 h-[420px] overflow-y-auto border border-border bg-card p-5"
            >
                {messages.length === 0 ? (
                    <div className="flex h-full flex-col items-center justify-center text-center">
                        <div className="mb-3 flex h-12 w-12 items-center justify-center bg-accent">
                            <Robot size={24} weight="duotone" />
                        </div>
                        <div className="font-display text-lg font-bold tracking-tight">
                            Ask me anything about this lecture
                        </div>
                        <p className="mt-1 max-w-sm text-sm text-muted-foreground">
                            I read every word and only answer using what was actually said.
                        </p>
                        <div className="mt-5 flex flex-wrap justify-center gap-2">
                            {SUGGESTIONS.map((s) => (
                                <button
                                    key={s}
                                    onClick={() => send(s)}
                                    data-testid={`chat-suggestion-${s.slice(0, 12).replace(/\s/g, "-").toLowerCase()}`}
                                    className="border border-border bg-background px-3 py-1.5 text-xs transition-all hover:border-primary/40"
                                >
                                    {s}
                                </button>
                            ))}
                        </div>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {messages.map((m) => (
                            <Bubble key={m.id} msg={m} />
                        ))}
                        {sending && <TypingBubble />}
                    </div>
                )}
            </div>

            <form
                onSubmit={(e) => {
                    e.preventDefault();
                    send();
                }}
                className="flex gap-2"
            >
                <Input
                    data-testid="chat-input"
                    placeholder="Ask a question about this lecture…"
                    value={q}
                    onChange={(e) => setQ(e.target.value)}
                    disabled={sending}
                />
                <Button type="submit" disabled={sending || !q.trim()} data-testid="chat-send-btn">
                    <PaperPlaneTilt size={16} weight="duotone" />
                </Button>
            </form>
            <p className="mt-2 text-xs text-muted-foreground">
                Answers are grounded in the lecture transcript only. No web facts.
            </p>
        </div>
    );
}

function Bubble({ msg }) {
    const isUser = msg.role === "user";
    return (
        <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}
            data-testid={`chat-msg-${msg.role}`}
        >
            <div
                className={`flex h-8 w-8 shrink-0 items-center justify-center ${
                    isUser ? "bg-primary text-primary-foreground" : "bg-accent text-accent-foreground"
                }`}
            >
                {isUser ? <User size={16} weight="duotone" /> : <Robot size={16} weight="duotone" />}
            </div>
            <div
                className={`max-w-[80%] border px-4 py-2.5 text-sm leading-relaxed ${
                    isUser
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-border bg-background"
                }`}
            >
                {isUser ? (
                    <span className="whitespace-pre-wrap">{msg.content}</span>
                ) : (
                    <div className="chat-markdown" data-testid={`chat-msg-${msg.role}-md`}>
                        <ReactMarkdown
                            components={{
                                p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                                ul: ({ children }) => <ul className="mb-2 list-disc space-y-1 pl-5 last:mb-0">{children}</ul>,
                                ol: ({ children }) => <ol className="mb-2 list-decimal space-y-1 pl-5 last:mb-0">{children}</ol>,
                                li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                                strong: ({ children }) => <strong className="font-bold text-foreground">{children}</strong>,
                                em: ({ children }) => <em className="italic">{children}</em>,
                                code: ({ children }) => (
                                    <code className="rounded bg-muted px-1 py-0.5 font-mono text-[13px]">{children}</code>
                                ),
                            }}
                        >
                            {msg.content}
                        </ReactMarkdown>
                    </div>
                )}
            </div>
        </motion.div>
    );
}

function TypingBubble() {
    return (
        <div className="flex gap-3">
            <div className="flex h-8 w-8 items-center justify-center bg-accent">
                <Robot size={16} weight="duotone" />
            </div>
            <div className="flex items-center gap-1 border border-border bg-background px-4 py-3">
                {[0, 1, 2].map((i) => (
                    <span
                        key={i}
                        className="h-1.5 w-1.5 animate-pulse bg-primary"
                        style={{ animationDelay: `${i * 0.15}s` }}
                    />
                ))}
            </div>
        </div>
    );
}
