import { cn } from "@/lib/utils"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import type { Message } from "@/store/chat-store"
import { Bot, User } from "lucide-react"

interface MessageBubbleProps {
    message: Message
}

export function MessageBubble({ message }: MessageBubbleProps) {
    const isUser = message.role === 'user'

    return (
        <div
            className={cn(
                "flex w-full gap-4 p-4",
                isUser ? "flex-row-reverse" : "flex-row"
            )}
        >
            <Avatar className="h-8 w-8 border">
                {isUser ? (
                    <AvatarFallback>
                        <User className="h-4 w-4" />
                    </AvatarFallback>
                ) : (
                    <AvatarFallback className="bg-primary text-white">
                        <Bot className="h-4 w-4" />
                    </AvatarFallback>
                )}
            </Avatar>

            <div
                className={cn(
                    "flex max-w-[80%] flex-col gap-2",
                    isUser ? "items-end" : "items-start"
                )}
            >
                <div
                    className={cn(
                        "rounded-lg px-4 py-2 text-sm",
                        isUser
                            ? "bg-primary text-white"
                            : "bg-surface text-text-primary border border-border"
                    )}
                >
                    {message.content}
                </div>
                <span className="text-xs text-text-muted">
                    {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
            </div>
        </div>
    )
}
