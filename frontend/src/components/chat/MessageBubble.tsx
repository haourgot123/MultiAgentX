import { cn } from "@/lib/utils"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { InlineFilePreview } from "@/components/InlineFilePreview"
import type { Message, FileCitation } from "@/store/chat-store"
import { Bot, User, Globe, FileText } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import rehypeRaw from "rehype-raw"
import { memo, useMemo } from "react"

interface MessageBubbleProps {
    message: Message
    fileCitations?: FileCitation[]
    onFileCitationClick?: (citation: FileCitation, messageId: number) => void
}

interface Source {
    url: string
    title: string
    favicon: string | null
    type: 'web' | 'citation'
}

const SOURCES_SECTION_HEADING_REGEX = /^(?:#{1,6}\s+)?(?:\d+(?:\.\d+)*\.?\s+)?(?:Sources|References|Nguon|Nguồn|Tai lieu tham khao|Tài liệu tham khảo)\s*:?$/im

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

// Parse ## Sources section to build citation map: number -> { url, title }
function parseCitationMap(content: string): Map<number, { url: string; title: string }> {
    const map = new Map<number, { url: string; title: string }>()
    const sectionMatch = content.match(SOURCES_SECTION_HEADING_REGEX)
    if (!sectionMatch || sectionMatch.index === undefined) return map
    
    const sectionContent = content.slice(sectionMatch.index)
    // Match lines like:
    // [1] [Title](url)
    // 1. [Title](url)
    // [1] Title - url
    // 1. Title - url
    const lineRegex = /^\s*(?:\[(\d+)\]|(\d+)\.)\s+(?:\[([^\]]+)\]\(([^)]+)\)|(.+))/gm
    let m
    while ((m = lineRegex.exec(sectionContent)) !== null) {
        const num = parseInt(m[1] || m[2])
        if (m[4]) {
            // markdown link form
            map.set(num, { url: m[4], title: m[3] || m[4] })
        } else if (m[5]) {
            // plain text form
            const rawText = m[5].trim()
            const urlMatch = rawText.match(/https?:\/\/\S+/)
            map.set(num, { url: urlMatch ? urlMatch[0] : '', title: rawText })
        }
    }
    return map
}

// Process citations in content to make them styled HTML elements
function processCitations(content: string, fileCitations?: FileCitation[]): string {
    // First, add spacing between consecutive citations like [1][2][3] -> [1] [2] [3]
    let processed = content.replace(/\]\s*\[/g, '] [')
    
    // Handle file citations [X.Y] format (e.g., [1.2], [1.5])
    // Always convert these to clickable badges, even if fileCitations is not yet available
    processed = processed.replace(/\[(\d+\.\d+)\](?!\()/g, (_match, label) => {
        const citation = fileCitations?.find(c => c.citation_label === label)
        const pageInfo = citation?.page_no ? `Page ${citation.page_no}` : ''
        const fileName = citation?.file_name || ''
        return `<a href="#file-citation-${label}" class="file-citation-badge" data-citation-label="${label}" data-page="${citation?.page_no || ''}" data-file-name="${fileName}" title="${fileName}${pageInfo ? ` ${pageInfo}` : ''}">[${label}]</a>`
    })
    
    // Convert web citation patterns [1], [2], etc. to styled superscript links
    // Only match standalone citations, not markdown links [text](url) and not file citations [X.Y]
    processed = processed.replace(/\[(\d+)\](?!\()/g, (_match, num) => {
        return `<a href="#citation-${num}" class="citation-badge" data-citation="${num}">${num}</a>`
    })
    
    return processed
}

function extractSources(content: string, fileCitations?: FileCitation[]): { sources: Source[]; contentWithoutSources: string } {
    // First process citations
    const processed = processCitations(content, fileCitations)
    
    const sources: Source[] = []
    const seenUrls = new Set<string>()
    
    // Check if content has a References or Sources section - links there should remain clickable
        const sourcesSectionMatch = content.match(SOURCES_SECTION_HEADING_REGEX)
        const sectionStartIndex = sourcesSectionMatch?.index ?? -1
    const hasReferencesSection = sectionStartIndex !== -1
    
    // 1. Extract markdown links: [title](url)
    const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g
    const stripNonNumericMarkdownLinks = (text: string) =>
        text.replace(linkRegex, (_match, title, url) => {
            if (/^\d+$/.test(title.trim())) {
                return `[${title}](${url})`
            }

            return title
        })
    let match
    
    while ((match = linkRegex.exec(content)) !== null) {
        const [, title, url] = match
        const matchIndex = match.index
        
        // Skip extraction if link is in References/Sources section
        if (hasReferencesSection && matchIndex > sectionStartIndex) {
            continue
        }
        
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
        const [, sourceNames] = citationMatch
        const matchIndex = citationMatch.index
        
        // Skip extraction if citation is in References/Sources section
        if (hasReferencesSection && matchIndex > sectionStartIndex) {
            continue
        }
        
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
    
    // Loại bỏ markdown links khỏi content (but preserve links in References/Sources section)
    let contentWithoutSources = processed
    if (hasReferencesSection) {
        // Split content at References/Sources section
        const beforeSection = processed.substring(0, sectionStartIndex)
        const sectionContent = processed.substring(sectionStartIndex)
        
        // Only replace links before References/Sources section
        const beforeProcessed = stripNonNumericMarkdownLinks(beforeSection)
        // Keep References/Sources section as-is (links remain clickable)
        contentWithoutSources = beforeProcessed + sectionContent
    } else {
        contentWithoutSources = stripNonNumericMarkdownLinks(processed)
    }
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
            {visibleSources.map((source) => (
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

function getPreviewUrl(fileUrl: string, filename: string): string {
    const extension = filename.split('.').pop()?.toLowerCase() || ''
    if (['doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx'].includes(extension)) {
        return `https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(fileUrl)}`
    }
    return fileUrl
}

function downloadFile(fileUrl: string, filename: string) {
    const anchor = document.createElement('a')
    anchor.href = fileUrl
    anchor.download = filename
    anchor.rel = 'noreferrer'
    document.body.appendChild(anchor)
    anchor.click()
    document.body.removeChild(anchor)
}

function isImageAttachment(message: Message): boolean {
    if (message.blobContentType?.startsWith('image/')) {
        return true
    }

    const extension = message.blobName?.split('.').pop()?.toLowerCase() || ''
    return ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'].includes(extension)
}

function MessageBubbleComponent({ message, fileCitations, onFileCitationClick }: MessageBubbleProps) {
    const isUser = message.role === 'user'
    const hasImageAttachment = !isUser && !!message.blobUrl && !!message.blobName && isImageAttachment(message)
    const hasNonImageAttachment = !isUser && !!message.blobUrl && !!message.blobName && !hasImageAttachment
    
    const { sources, contentWithoutSources, citationMap } = useMemo(() => {
        if (isUser) {
            return { sources: [], contentWithoutSources: message.content, citationMap: new Map<number, { url: string; title: string }>() }
        }
        const extracted = extractSources(message.content, fileCitations)
        const cMap = parseCitationMap(message.content)
        return { ...extracted, citationMap: cMap }
    }, [message.content, isUser, fileCitations])

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
                            rehypePlugins={[rehypeRaw]}
                            components={{
                                p: ({ children }) => <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>,
                                a: ({ href, children, className, ...props }) => {
                                    // File citation badges [X.Y] - clickable to navigate PDF
                                    if (className === 'file-citation-badge' || href?.startsWith('#file-citation-')) {
                                        const label = (props as Record<string, string>)['data-citation-label'] || ''
                                        const citation = fileCitations?.find(c => c.citation_label === label)
                                        const dataPage = (props as Record<string, string>)['data-page']
                                        const dataFileName = (props as Record<string, string>)['data-file-name']
                                        const pageNo = citation?.page_no ?? (dataPage ? Number(dataPage) || null : null)
                                        const fileName = citation?.file_name || dataFileName || ''
                                        const handleClick = (e: React.MouseEvent) => {
                                            e.preventDefault()
                                            const citationObj: FileCitation = citation || {
                                                citation_label: label,
                                                file_id: 0,
                                                file_name: fileName,
                                                page_no: pageNo,
                                                chunk_index: 0,
                                            }
                                            onFileCitationClick?.(citationObj, message.id)
                                        }
                                        return (
                                            <TooltipProvider delayDuration={120}>
                                                <Tooltip>
                                                    <TooltipTrigger asChild>
                                                        <a
                                                            href="#"
                                                            onClick={handleClick}
                                                            className="inline-flex items-center justify-center min-w-[2rem] h-5 text-[10px] font-bold text-white bg-amber-500 hover:bg-amber-600 rounded-full px-1.5 no-underline cursor-pointer transition-all duration-200 hover:scale-110 shadow-sm mx-0.5 align-super"
                                                            title={`${fileName}${pageNo ? ` — Page ${pageNo}` : ''}`}
                                                            {...props}
                                                        >
                                                            {children}
                                                        </a>
                                                    </TooltipTrigger>
                                                    <TooltipContent side="top" className="max-w-xs">
                                                        <div className="text-sm font-medium">{fileName || `Document citation ${label}`}</div>
                                                        <div className="text-xs text-muted-foreground">
                                                            {pageNo ? `Page ${pageNo}` : 'Document reference'}
                                                        </div>
                                                        <div className="text-xs text-muted-foreground">Click to open this citation</div>
                                                    </TooltipContent>
                                                </Tooltip>
                                            </TooltipProvider>
                                        )
                                    }
                                    // Citation badge links - styled inline numbered badges
                                    if (className === 'citation-badge' || href?.startsWith('#citation-')) {
                                        const citationNum = href ? parseInt(href.replace('#citation-', '')) : NaN
                                        const citationInfo = !isNaN(citationNum) ? citationMap.get(citationNum) : undefined
                                        const isClickable = Boolean(citationInfo?.url)
                                        const handleClick = (e: React.MouseEvent) => {
                                            e.preventDefault()
                                            if (isClickable && citationInfo?.url) {
                                                window.open(citationInfo.url, '_blank', 'noreferrer')
                                            }
                                        }
                                        const tooltipText = citationInfo
                                            ? `${citationInfo.title}${citationInfo.url ? `\n${citationInfo.url}` : ''}`
                                            : `Source ${children} is not available`
                                        return (
                                            <TooltipProvider delayDuration={120}>
                                                <Tooltip>
                                                    <TooltipTrigger asChild>
                                                        <a
                                                            href={isClickable ? citationInfo?.url : undefined}
                                                            target={isClickable ? '_blank' : undefined}
                                                            rel={isClickable ? 'noreferrer' : undefined}
                                                            onClick={isClickable ? handleClick : undefined}
                                                            aria-disabled={!isClickable}
                                                            className={cn(
                                                                "inline-flex items-center justify-center min-w-[1.25rem] h-5 text-[10px] font-bold rounded-full px-1.5 no-underline shadow-sm mx-0.5 align-super transition-all duration-200",
                                                                isClickable
                                                                    ? "text-white bg-primary hover:bg-primary/80 cursor-pointer hover:scale-110"
                                                                    : "text-white/90 bg-muted-foreground/60 cursor-default"
                                                            )}
                                                            title={tooltipText}
                                                            {...props}
                                                        >
                                                            {children}
                                                        </a>
                                                    </TooltipTrigger>
                                                    <TooltipContent side="top" className="max-w-xs">
                                                        <div className="text-sm font-medium">
                                                            {citationInfo?.title || `Source ${children}`}
                                                        </div>
                                                        <div className="text-xs text-muted-foreground break-all">
                                                            {citationInfo?.url || 'Source link unavailable'}
                                                        </div>
                                                        <div className="text-xs text-muted-foreground">
                                                            {isClickable ? 'Click to open source' : 'Preview unavailable'}
                                                        </div>
                                                    </TooltipContent>
                                                </Tooltip>
                                            </TooltipProvider>
                                        )
                                    }
                                    // Extracted source links - show as styled text
                                    if (sources.some(s => s.url === href)) {
                                        const linkText = typeof children === 'string' ? children : Array.isArray(children) ? children.join('') : ''
                                        if (/^\d+$/.test(linkText.trim())) {
                                            return (
                                                <a
                                                    href={href}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                    className="inline-flex items-center justify-center min-w-[1.25rem] h-5 text-[10px] font-bold text-white bg-primary hover:bg-primary/80 rounded-full px-1.5 no-underline cursor-pointer transition-all duration-200 hover:scale-110 shadow-sm mx-0.5 align-super"
                                                    {...props}
                                                >
                                                    {children}
                                                </a>
                                            )
                                        }

                                        return <span className="underline decoration-primary/60 hover:decoration-primary cursor-pointer">{children}</span>
                                    }
                                    // Regular external links
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

                {hasImageAttachment && (
                    <div className="mt-2 w-full max-w-[38rem] overflow-hidden rounded-2xl border border-border bg-surface">
                        <a
                            href={message.blobUrl as string}
                            target="_blank"
                            rel="noreferrer"
                            className="block"
                        >
                            <img
                                src={message.blobUrl as string}
                                alt={message.blobName as string}
                                className="max-h-[32rem] w-full object-contain bg-slate-50"
                            />
                        </a>
                    </div>
                )}

                {hasNonImageAttachment && (
                    <div className="mt-2 w-full max-w-[38rem]">
                        <InlineFilePreview
                            fileUrl={message.blobUrl as string}
                            filename={message.blobName as string}
                            onView={() => window.open(getPreviewUrl(message.blobUrl as string, message.blobName as string), '_blank', 'noreferrer')}
                            onDownload={() => downloadFile(message.blobUrl as string, message.blobName as string)}
                        />
                    </div>
                )}
                
                <span className="text-xs text-text-muted mt-1">
                    {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
            </div>
        </div>
    )
}

export const MessageBubble = memo(
    MessageBubbleComponent,
    (previousProps, nextProps) =>
        previousProps.message === nextProps.message &&
        previousProps.fileCitations === nextProps.fileCitations &&
        previousProps.onFileCitationClick === nextProps.onFileCitationClick
)
