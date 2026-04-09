import { cn } from "@/lib/utils"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import type { Message } from "@/store/chat-store"
import { Bot, User, Globe, FileText } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { useMemo } from "react"

interface MessageBubbleProps {
    message: Message
}

interface Source {
    url: string
    title: string
    favicon: string | null
    type: 'web' | 'citation'
}

function getFaviconUrl(href: string): string | null {
    try {
        const url = new URL(href)
        return `https://www.google.com/s2/favicons?domain=${encodeURIComponent(url.hostname)}&sz=32`
    } catch {
        return null
    }
}

// Map các source name phổ biến với URL
const sourceUrlMap: Record<string, string> = {
    'FPT Software': 'https://fptsoftware.com',
    'Microsoft': 'https://microsoft.com',
    'Microsoft Source': 'https://news.microsoft.com/source/',
    'IBM': 'https://ibm.com',
    'IBM Think': 'https://ibm.com/think',
    'Stanford HAI': 'https://hai.stanford.edu',
    'Stanford': 'https://stanford.edu',
    'MIT': 'https://mit.edu',
    'MIT Sloan Review': 'https://sloanreview.mit.edu',
    'PwC': 'https://pwc.com',
    'Forbes': 'https://forbes.com',
    'EAIT 2026': 'https://eait.org',
    'Sapphire Ventures': 'https://sapphireventures.com',
}

function extractSources(content: string): { sources: Source[]; contentWithoutSources: string } {
    const sources: Source[] = []
    const seenUrls = new Set<string>()
    
    // 1. Extract markdown links: [title](url)
    const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g
    let match
    
    while ((match = linkRegex.exec(content)) !== null) {
        const [fullMatch, title, url] = match
        if (!seenUrls.has(url) && url.startsWith('http')) {
            seenUrls.add(url)
            sources.push({
                url,
                title: title || url,
                favicon: getFaviconUrl(url),
                type: 'web'
            })
        }
    }
    
    // 2. Extract citations: (Source: XXX) hoặc (Sources: XXX, YYY)
    const citationRegex = /\(Source(?:s)?:\s*([^)]+)\)/g
    let citationMatch
    
    while ((citationMatch = citationRegex.exec(content)) !== null) {
        const [fullMatch, sourceNames] = citationMatch
        // Tách các source name nếu có nhiều (phân cách bởi dấu phẩy hoặc "và")
        const names = sourceNames.split(/,\s*|\s+and\s+/).map(n => n.trim()).filter(Boolean)
        
        for (const name of names) {
            // Tìm URL tương ứng
            const url = sourceUrlMap[name] || `https://www.google.com/search?q=${encodeURIComponent(name)}`
            
            if (!seenUrls.has(url)) {
                seenUrls.add(url)
                sources.push({
                    url,
                    title: name,
                    favicon: getFaviconUrl(url),
                    type: 'citation'
                })
            }
        }
    }
    
    // Loại bỏ markdown links khỏi content
    let contentWithoutSources = content.replace(linkRegex, '$1')
    // Loại bỏ citation tags khỏi content
    contentWithoutSources = contentWithoutSources.replace(citationRegex, '')
    
    return { sources, contentWithoutSources }
}

function SourceIcons({ sources }: { sources: Source[] }) {
    const maxVisible = 6
    const visibleSources = sources.slice(0, maxVisible)
    const remainingCount = sources.length - maxVisible
    
    return (
        <div className="flex items-center gap-1 mt-2">
            {visibleSources.map((source, index) => (
                <TooltipProvider key={source.url} delayDuration={100}>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <a
                                href={source.url}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center justify-center w-7 h-7 rounded-lg hover:bg-muted/80 transition-colors border border-transparent hover:border-border"
                            >
                                {source.favicon ? (
                                    <img
                                        src={source.favicon}
                                        alt=""
                                        className="w-5 h-5 object-contain"
                                        loading="lazy"
                                        referrerPolicy="no-referrer"
                                    />
                                ) : source.type === 'citation' ? (
                                    <FileText className="w-4 h-4 text-muted-foreground" />
                                ) : (
                                    <Globe className="w-4 h-4 text-muted-foreground" />
                                )}
                            </a>
                        </TooltipTrigger>
                        <TooltipContent side="bottom" className="max-w-xs">
                            <p className="text-sm font-medium">{source.title}</p>
                            <p className="text-xs text-muted-foreground truncate">{source.url}</p>
                        </TooltipContent>
                    </Tooltip>
                </TooltipProvider>
            ))}
            {remainingCount > 0 && (
                <TooltipProvider delayDuration={100}>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <span className="inline-flex items-center justify-center w-7 h-7 text-sm font-medium text-muted-foreground hover:text-foreground cursor-pointer hover:bg-muted/80 rounded-lg transition-colors">
                                +{remainingCount}
                            </span>
                        </TooltipTrigger>
                        <TooltipContent side="bottom">
                            <p className="text-sm">{remainingCount} more sources</p>
                        </TooltipContent>
                    </Tooltip>
                </TooltipProvider>
            )}
        </div>
    )
}

export function MessageBubble({ message }: MessageBubbleProps) {
    const isUser = message.role === 'user'
    
    const { sources, contentWithoutSources } = useMemo(() => {
        if (isUser) {
            return { sources: [], contentWithoutSources: message.content }
        }
        return extractSources(message.content)
    }, [message.content, isUser])

    return (
        <div
            className={cn(
                "flex w-full gap-4 p-4",
                isUser ? "flex-row-reverse" : "flex-row"
            )}
        >
            <Avatar className="h-10 w-10 border">
                {isUser ? (
                    <AvatarFallback>
                        <User className="h-5 w-5" />
                    </AvatarFallback>
                ) : (
                    <AvatarFallback className="bg-primary text-white">
                        <Bot className="h-5 w-5" />
                    </AvatarFallback>
                )}
            </Avatar>

            <div
                className={cn(
                    "flex max-w-[85%] flex-col gap-1.5",
                    isUser ? "items-end" : "items-start"
                )}
            >
                <div
                    className={cn(
                        "rounded-xl px-5 py-3 text-[15px] leading-relaxed",
                        isUser
                            ? "bg-primary text-white"
                            : "bg-surface text-text-primary border border-border prose dark:prose-invert max-w-none prose-p:leading-relaxed prose-pre:p-0 prose-base"
                    )}
                >
                    {isUser ? (
                        <div className="whitespace-pre-wrap">{message.content}</div>
                    ) : (
                        <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                                p: ({ children }) => <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>,
                                a: ({ href, children, ...props }) => {
                                    // Nếu là link trong sources, chỉ hiển thị text
                                    if (sources.some(s => s.url === href)) {
                                        return <span className="underline decoration-primary/60 hover:decoration-primary cursor-pointer">{children}</span>
                                    }
                                    // Link khác vẫn render bình thường
                                    return (
                                        <a
                                            href={href}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="text-primary underline-offset-2 hover:underline font-medium"
                                            {...props}
                                        >
                                            {children}
                                        </a>
                                    )
                                },
                            }}
                        >
                            {contentWithoutSources}
                        </ReactMarkdown>
                    )}
                </div>
                
                {/* Hiển thị sources dưới dạng icon row */}
                {!isUser && sources.length > 0 && (
                    <SourceIcons sources={sources} />
                )}
                
                <span className="text-xs text-text-muted mt-1">
                    {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
            </div>
        </div>
    )
}
