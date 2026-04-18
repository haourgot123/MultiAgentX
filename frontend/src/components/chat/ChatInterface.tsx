import { useEffect, useRef, useState } from "react"
import { useChatStore, type FileCitation } from "@/store/chat-store"
import { useFileStore } from "@/store/file-store"
import { MessageBubble } from "./MessageBubble"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Send, Paperclip, Image as ImageIcon, Search, Globe, Aperture, X, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Toggle } from "@/components/ui/toggle"
import { useLocation } from "react-router-dom"
import { toast } from "sonner"
import { PlanApprovalModal } from "./PlanApprovalModal"

interface ChatInterfaceProps {
    onFileCitationClick?: (citation: FileCitation, messageId: number) => void
    selectedFileIds?: number[]
}

export function ChatInterface({ onFileCitationClick, selectedFileIds }: ChatInterfaceProps) {
    const location = useLocation()
    const {
        getCurrentMessages,
        input,
        setInput,
        isLoading,
        loadingChatId,
        conversationOpenScrollBehavior,
        setConversationOpenScrollBehavior,
        statusSteps,
        currentChatId,
        chatSessions,
        messagesByChat,
        pendingPlan,
        researchPhase,
        addMessage,
        loadConversation,
        createDeepResearchPlan,
        approveDeepResearchPlan,
        setPendingPlan,
    } = useChatStore()
    const files = useFileStore((state) => state.files)
    const fileChatCitations = useChatStore((state) => state.fileChatCitations)
    const messages = getCurrentMessages()
    const isCurrentChatLoading = currentChatId !== null && loadingChatId === currentChatId
    const currentStatusSteps = isCurrentChatLoading ? statusSteps : []
    const visibleStatusSteps = currentStatusSteps.slice(-3)
    const currentLastMessage = messages[messages.length - 1]
    const hasStreamingAssistantMessage =
        isCurrentChatLoading &&
        currentLastMessage?.role === 'assistant' &&
        currentLastMessage.content.trim().length > 0
    const scrollAreaRef = useRef<HTMLDivElement>(null)
    const scrollRef = useRef<HTMLDivElement>(null)
    const shouldAutoScrollRef = useRef(true)
    const pendingConversationJumpRef = useRef(true)
    const previousChatIdRef = useRef<number | null>(null)
    const previousMessageCountRef = useRef(0)
    const previousLastMessageIdRef = useRef<number | null>(null)

    const isFileChat = location.pathname === '/chat-file'
    const currentFileSession =
        isFileChat && currentChatId
            ? chatSessions.find(
                (session) => session.id === currentChatId && session.chatType === 'file'
            ) || null
            : null
    const attachedFiles = currentFileSession
        ? files.filter((file) => currentFileSession.fileIds.includes(file.id))
        : []
    const selectedAttachedFiles = isFileChat
        ? (
            selectedFileIds && selectedFileIds.length > 0
                ? attachedFiles.filter((file) => selectedFileIds.includes(file.id))
                : selectedFileIds
                    ? []
                    : attachedFiles
        )
        : []
    const completedFiles = attachedFiles.filter(
        (file) => file.ingestionStatus === 'completed'
    )
    const selectedCompletedFiles = selectedAttachedFiles.filter(
        (file) => file.ingestionStatus === 'completed'
    )
    const hasActiveIngestion = attachedFiles.some((file) =>
        ['pending', 'parsing', 'chunking', 'embedding', 'indexing', 'processing'].includes(
            file.ingestionStatus
        )
    )
    const allAttachedFilesFailed =
        attachedFiles.length > 0 &&
        attachedFiles.every((file) => file.ingestionStatus === 'failed')
    const fileChatBlocked =
        isFileChat &&
        (
            !currentFileSession ||
            attachedFiles.length === 0 ||
            completedFiles.length === 0 ||
            (selectedFileIds !== undefined && selectedAttachedFiles.length === 0) ||
            (
                selectedFileIds !== undefined &&
                selectedAttachedFiles.length > 0 &&
                selectedCompletedFiles.length === 0
            )
        )
    const fileChatBlockReason = !currentFileSession || attachedFiles.length === 0
        ? 'Attach at least one file to this conversation before chatting.'
        : selectedFileIds !== undefined && selectedAttachedFiles.length === 0
            ? 'Select at least one file to chat with.'
            : selectedFileIds !== undefined && selectedAttachedFiles.length > 0 && selectedCompletedFiles.length === 0
                ? 'Selected files are not ready yet. Choose at least one Completed file.'
        : hasActiveIngestion
            ? 'Ingestion is still running. Wait until at least one file is Completed.'
            : allAttachedFilesFailed
                ? 'All attached files failed ingestion. Upload another file or retry ingestion.'
                : 'At least one attached file must be Completed before chatting.'
    const inputPlaceholder = fileChatBlocked
        ? fileChatBlockReason
        : "Ask anything..."

    const ResearchChaseIndicator = ({ className }: { className?: string }) => (
        <div className={cn("research-chase", className)} aria-hidden="true">
            <span className="research-chase-dot" />
            <span className="research-chase-dot" />
            <span className="research-chase-dot" />
        </div>
    )

    const renderResearchStatusCard = (label: string) => (
        <div
            className="research-step-active flex items-center gap-3 overflow-hidden rounded-2xl border border-primary/15 bg-white/80 px-3 py-2.5 shadow-[0_14px_30px_rgba(18,130,79,0.08)]"
            aria-live="polite"
        >
            <ResearchChaseIndicator className="shrink-0" />
            <span className="text-sm font-medium text-text-primary">{label}</span>
        </div>
    )

    const renderResearchTrail = (steps: string[]) => (
        <div className="space-y-2 animate-in fade-in duration-300" aria-live="polite">
            {steps.map((step, idx) => {
                const isActiveStep = idx === steps.length - 1

                return (
                    <div
                        key={`${step}-${idx}`}
                        className={cn(
                            "flex items-start gap-3 rounded-2xl border px-3 py-2.5 transition-all duration-300",
                            isActiveStep
                                ? "research-step-active overflow-hidden border-primary/15 bg-white/85 shadow-[0_14px_30px_rgba(18,130,79,0.08)]"
                                : "border-transparent bg-white/45 opacity-70"
                        )}
                    >
                        <div className="mt-0.5 flex h-5 w-6 shrink-0 items-center">
                            {isActiveStep ? (
                                <ResearchChaseIndicator />
                            ) : (
                                <div className="h-2.5 w-2.5 rounded-full bg-primary/35" />
                            )}
                        </div>
                        <span
                            className={cn(
                                "text-sm font-medium leading-5",
                                isActiveStep ? "text-text-primary" : "text-text-muted"
                            )}
                        >
                            {step}
                        </span>
                    </div>
                )
            })}
        </div>
    )

    const renderStatusTrail = (steps: string[]) => (
        <div className="flex flex-col gap-2" aria-live="polite">
            {steps.map((step, idx) => {
                const distanceFromActive = steps.length - idx - 1
                const isActiveStep = distanceFromActive === 0

                return (
                    <div
                        key={`${step}-${idx}`}
                        className={cn(
                            "flex items-center gap-3 rounded-xl px-3 py-2 transition-all duration-300",
                            isActiveStep
                                ? "bg-primary/8 opacity-100 shadow-sm ring-1 ring-primary/10"
                                : distanceFromActive === 1
                                    ? "opacity-60"
                                    : "opacity-35"
                        )}
                    >
                        <div className="flex h-5 w-5 items-center justify-center">
                            {isActiveStep ? (
                                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                            ) : (
                                <div className="h-2.5 w-2.5 rounded-full bg-primary/45" />
                            )}
                        </div>
                        <span
                            className={cn(
                                "text-sm font-medium",
                                isActiveStep ? "text-text-primary" : "text-text-muted"
                            )}
                        >
                            {step}
                        </span>
                    </div>
                )
            })}
        </div>
    )

    const [activeFeatures, setActiveFeatures] = useState({
        deepResearch: false,
        webSearch: false,
        genImage: false,
    })
    const routePreference: 'auto' | 'websearch_agent' | 'deep_research_agent' | 'image_generation_agent' =
        activeFeatures.webSearch
            ? 'websearch_agent'
            : activeFeatures.genImage
                ? 'image_generation_agent'
                : activeFeatures.deepResearch
                    ? 'deep_research_agent'
                    : 'auto'
    const chatOptions = isFileChat
        ? {
            is_web_search_enabled: false,
            is_deep_research_enabled: false,
            is_generate_image_enabled: false,
            route_preference: 'auto' as const,
        }
        : {
            is_web_search_enabled: true,
            is_deep_research_enabled: false,
            is_generate_image_enabled: true,
            route_preference: routePreference,
        }

    const toggleFeature = (feature: keyof typeof activeFeatures) => {
        setActiveFeatures((prev) => {
            const nextValue = !prev[feature]
            if (!nextValue) {
                return { ...prev, [feature]: false }
            }

            return {
                deepResearch: false,
                webSearch: false,
                genImage: false,
                [feature]: true,
            }
        })
    }

    useEffect(() => {
        if (isFileChat) {
            setActiveFeatures({
                deepResearch: false,
                webSearch: false,
                genImage: false,
            })
        }
    }, [isFileChat])

    useEffect(() => {
        if (!currentChatId) {
            return
        }

        const currentSession = chatSessions.find((session) => session.id === currentChatId)
        if (!currentSession) {
            return
        }

        if (messagesByChat[currentChatId] !== undefined) {
            return
        }

        void loadConversation(currentChatId)
    }, [currentChatId, chatSessions, messagesByChat, loadConversation])

    useEffect(() => {
        if (currentChatId === previousChatIdRef.current) {
            return
        }

        previousChatIdRef.current = currentChatId
        pendingConversationJumpRef.current = true
        shouldAutoScrollRef.current = true
        previousMessageCountRef.current = 0
        previousLastMessageIdRef.current = null
    }, [currentChatId])

    useEffect(() => {
        return () => {
            setConversationOpenScrollBehavior(null)
        }
    }, [setConversationOpenScrollBehavior])

    useEffect(() => {
        const viewport = scrollAreaRef.current?.querySelector(
            '[data-radix-scroll-area-viewport]'
        ) as HTMLDivElement | null

        if (!viewport) {
            return
        }

        const updateAutoScrollState = () => {
            const distanceFromBottom = viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight
            shouldAutoScrollRef.current = distanceFromBottom <= 96
        }

        updateAutoScrollState()
        viewport.addEventListener('scroll', updateAutoScrollState, { passive: true })

        return () => {
            viewport.removeEventListener('scroll', updateAutoScrollState)
        }
    }, [])

    useEffect(() => {
        if (!scrollRef.current) {
            return
        }

        const lastMessage = messages[messages.length - 1]

        if (pendingConversationJumpRef.current) {
            if (messages.length === 0) {
                return
            }

            scrollRef.current.scrollIntoView({
                behavior: conversationOpenScrollBehavior || "auto",
                block: "end",
            })

            pendingConversationJumpRef.current = false
            setConversationOpenScrollBehavior(null)
            shouldAutoScrollRef.current = true
            previousMessageCountRef.current = messages.length
            previousLastMessageIdRef.current = lastMessage?.id ?? null
            return
        }

        const hasNewMessage = messages.length > previousMessageCountRef.current
        const hasMessageBoundaryChanged = lastMessage?.id !== previousLastMessageIdRef.current
        const isUserMessage = lastMessage?.role === 'user'
        const isStreamingAssistantUpdate = isCurrentChatLoading && lastMessage?.role === 'assistant'

        if (isStreamingAssistantUpdate) {
            previousMessageCountRef.current = messages.length
            previousLastMessageIdRef.current = lastMessage?.id ?? null
            return
        }

        if (!shouldAutoScrollRef.current && !isUserMessage) {
            previousMessageCountRef.current = messages.length
            previousLastMessageIdRef.current = lastMessage?.id ?? null
            return
        }

        scrollRef.current.scrollIntoView({
            behavior: hasNewMessage || hasMessageBoundaryChanged ? "smooth" : "auto",
            block: "end",
        })

        shouldAutoScrollRef.current = true

        previousMessageCountRef.current = messages.length
        previousLastMessageIdRef.current = lastMessage?.id ?? null
    }, [messages, conversationOpenScrollBehavior, isCurrentChatLoading, setConversationOpenScrollBehavior])

    const handleSend = async () => {
        if (fileChatBlocked) {
            toast.error(fileChatBlockReason)
            return
        }
        if (!input.trim()) return

        const prompt = input
        const userMessage = {
            role: 'user' as const,
            content: prompt,
        }
        
        // Deep Research persists the user message first, then requests a plan.
        if (!isFileChat && activeFeatures.deepResearch) {
            setInput("")
            
            try {
                await addMessage(userMessage, 'normal')

                const activeChatId = useChatStore.getState().currentChatId
                if (!activeChatId) {
                    throw new Error('No active conversation')
                }
                
                // Create research plan - backend will emit status events
                const planRequest = await createDeepResearchPlan(activeChatId, prompt)
                
                // Show plan approval modal
                setPendingPlan(planRequest)
            } catch (error) {
                toast.error('Failed to create research plan')
                console.error(error)
                setInput(prompt)
            }
            return
        }

        setInput("")
        
        try {
            // Normal chat flow
            await useChatStore.getState().streamChat(
                userMessage,
                isFileChat ? 'file' : 'normal',
                isFileChat
                    ? {
                        ...chatOptions,
                        file_ids: selectedFileIds,
                    }
                    : chatOptions
            )
        } catch {
            setInput(prompt)
            toast.error('Failed to send message')
        }
    }

    const handlePlanApprove = async (approvedPlan: string[], sessionId: string) => {
        try {
            await approveDeepResearchPlan(sessionId, approvedPlan)
            toast.success('Research started with approved plan')
        } catch (error) {
            toast.error('Failed to start research')
            console.error(error)
        }
    }

    const handlePlanCancel = () => {
        setPendingPlan(null)
        toast.info('Research cancelled')
    }

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault()
            handleSend()
        }
    }

    return (
        <div className="flex h-full w-full relative">
            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col h-full w-full max-w-4xl mx-auto relative z-0">
                <div className="flex-1 overflow-hidden p-4">
                    <ScrollArea ref={scrollAreaRef} className="h-full pr-4">
                        <div className="flex flex-col gap-6 pb-4">
                            {messages.length === 0 && (
                                <div className="flex flex-col items-center justify-center h-[60vh] text-center space-y-6">
                                    <div className="h-20 w-20 rounded-[2rem] bg-tech-gradient flex items-center justify-center shadow-[0_24px_55px_rgba(18,130,79,0.28)] ring-1 ring-emerald-400/20 animate-in zoom-in duration-500">
                                        <Aperture className="h-10 w-10 text-white" />
                                    </div>
                                    <div className="space-y-2">
                                        <h3 className="font-display text-2xl font-bold tracking-tight text-text-primary">MultiAgentX</h3>
                                        <p className="text-text-muted max-w-sm mx-auto">
                                            Your advanced AI assistant for research, analysis, and creation.
                                        </p>
                                    </div>
                                </div>
                            )}
                            {messages.map((msg) => (
                                <MessageBubble
                                    key={msg.id}
                                    message={msg}
                                    fileCitations={isFileChat && currentChatId ? fileChatCitations[currentChatId] : undefined}
                                    onFileCitationClick={isFileChat ? onFileCitationClick : undefined}
                                />
                            ))}
                            {/* Deep Research - show current status */}
                            {activeFeatures.deepResearch && isCurrentChatLoading && !hasStreamingAssistantMessage && (
                                <div className="p-4 animate-in fade-in duration-300">
                                    {renderResearchStatusCard(
                                        researchPhase === 'researching'
                                            ? (currentStatusSteps.length > 0 ? currentStatusSteps[currentStatusSteps.length - 1] : 'Researching...')
                                            : researchPhase === 'planning'
                                                ? 'Creating research plan...'
                                                : (pendingPlan ? 'Review plan before starting...' : 'Processing...')
                                    )}
                                </div>
                            )}
                            {/* Show status steps in Chat only when NOT using Deep Research */}
                            {(currentStatusSteps.length > 0 || (isCurrentChatLoading && !hasStreamingAssistantMessage)) && !activeFeatures.deepResearch && (
                                <div className="p-4 animate-in fade-in duration-300">
                                    {visibleStatusSteps.length > 0 ? (
                                        renderStatusTrail(visibleStatusSteps)
                                    ) : (
                                        <div className="text-sm text-text-muted">
                                            {isCurrentChatLoading && pendingPlan === null ? 'Processing...' : 
                                             pendingPlan ? 'Review plan before starting...' : 
                                             'Waiting for input...'}
                                        </div>
                                    )}
                                </div>
                            )}
                            <div ref={scrollRef} />
                        </div>
                    </ScrollArea>
                </div>

                {/* Input Area */}
                <div className="p-4 bg-white pb-8">
                    <div className="relative flex flex-col gap-2 rounded-2xl border border-border bg-surface shadow-sm p-3 focus-within:ring-1 focus-within:ring-primary/50 transition-all duration-200">
                        <Textarea
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder={inputPlaceholder}
                            disabled={isCurrentChatLoading || fileChatBlocked}
                            className="min-h-[40px] max-h-[200px] w-full resize-none border-0 bg-transparent p-2 placeholder:text-text-muted focus-visible:ring-0 focus-visible:ring-offset-0 text-base"
                            rows={1}
                            style={{ height: 'auto', minHeight: '44px' }}
                            onInput={(e) => {
                                const target = e.target as HTMLTextAreaElement;
                                target.style.height = 'auto';
                                target.style.height = `${target.scrollHeight}px`;
                            }}
                        />

                        <div className="flex items-center justify-between mt-2">
                            <div className="flex items-center gap-1">
                                {!isFileChat && (
                                    <>
                                        <TooltipProvider>
                                            <Tooltip>
                                                <TooltipTrigger asChild>
                                                    <Button variant="ghost" size="icon" className="h-8 w-8 rounded-lg text-text-muted hover:text-primary hover:bg-primary/10">
                                                        <Paperclip className="h-4 w-4" />
                                                    </Button>
                                                </TooltipTrigger>
                                                <TooltipContent>Attach File</TooltipContent>
                                            </Tooltip>
                                        </TooltipProvider>

                                        <div className="h-4 w-px bg-border/50 mx-1" />

                                        <TooltipProvider>
                                            <Tooltip>
                                                <TooltipTrigger asChild>
                                                    <Toggle
                                                        pressed={activeFeatures.deepResearch}
                                                        onPressedChange={() => toggleFeature('deepResearch')}
                                                        className={cn(
                                                            "h-8 px-2 gap-2",
                                                            activeFeatures.deepResearch && "!bg-[#22c55e] !text-white hover:!bg-[#16a34a]"
                                                        )}
                                                    >
                                                        <Search className="h-4 w-4" />
                                                        <span className="text-xs font-medium">Deep Research</span>
                                                    </Toggle>
                                                </TooltipTrigger>
                                                <TooltipContent>Deep Research Mode</TooltipContent>
                                            </Tooltip>
                                        </TooltipProvider>

                                        <TooltipProvider>
                                            <Tooltip>
                                                <TooltipTrigger asChild>
                                                    <Toggle
                                                        pressed={activeFeatures.webSearch}
                                                        onPressedChange={() => toggleFeature('webSearch')}
                                                        size="sm"
                                                        className={cn(
                                                            "h-8 w-8 p-0",
                                                            activeFeatures.webSearch && "!bg-[#22c55e] !text-white hover:!bg-[#16a34a]"
                                                        )}
                                                    >
                                                        <Globe className="h-4 w-4" />
                                                    </Toggle>
                                                </TooltipTrigger>
                                                <TooltipContent>Web Search</TooltipContent>
                                            </Tooltip>
                                        </TooltipProvider>

                                        <TooltipProvider>
                                            <Tooltip>
                                                <TooltipTrigger asChild>
                                                    <Toggle
                                                        pressed={activeFeatures.genImage}
                                                        onPressedChange={() => toggleFeature('genImage')}
                                                        size="sm"
                                                        className={cn(
                                                            "h-8 w-8 p-0",
                                                            activeFeatures.genImage && "!bg-[#22c55e] !text-white hover:!bg-[#16a34a]"
                                                        )}
                                                    >
                                                        <ImageIcon className="h-4 w-4" />
                                                    </Toggle>
                                                </TooltipTrigger>
                                                <TooltipContent>Generate Image</TooltipContent>
                                            </Tooltip>
                                        </TooltipProvider>

                                    </>
                                )}
                            </div>

                            <div className="flex items-center gap-2">
                                <Button
                                    onClick={handleSend}
                                    disabled={!input.trim() || isCurrentChatLoading || fileChatBlocked}
                                    size="icon"
                                    className={cn(
                                        "h-8 w-8 rounded-full transition-all duration-200",
                                        input.trim() ? "bg-primary hover:bg-primary-hover text-white shadow-md" : "bg-surface text-text-muted"
                                    )}
                                >
                                    <Send className="h-4 w-4" />
                                </Button>
                            </div>
                        </div>
                    </div>
                    {isFileChat && fileChatBlocked && (
                        <div className="mt-2 text-center text-xs text-amber-700">
                            {fileChatBlockReason}
                        </div>
                    )}
                    <div className="mt-2 text-center text-xs text-text-muted">
                        MultiAgentX can make mistakes. Check important info.
                    </div>
                </div>
            </div>

            {/* Deep Research Panel (Conditional) */}
            {!isFileChat && activeFeatures.deepResearch && (
                <div className="w-80 border-l border-border bg-surface h-full flex flex-col transition-all duration-300 animate-in slide-in-from-right">
                    <div className="h-14 border-b border-border flex items-center justify-between px-4">
                        <div className="font-semibold text-sm flex items-center gap-2">
                            <Search className="h-4 w-4 text-primary" />
                            Deep Research
                        </div>
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => toggleFeature('deepResearch')}>
                            <X className="h-4 w-4" />
                        </Button>
                    </div>
                    <div className="p-4 space-y-4 overflow-auto flex-1">
                        <div className="p-3 rounded-lg bg-primary/5 border border-primary/20">
                            <div className="text-xs font-medium text-primary mb-2 uppercase tracking-wider">Current Task</div>
                            {currentStatusSteps.length > 0 ? (
                                renderResearchTrail(currentStatusSteps)
                            ) : isCurrentChatLoading && researchPhase === 'planning' ? (
                                renderResearchStatusCard('Creating research plan...')
                            ) : isCurrentChatLoading && researchPhase === 'researching' ? (
                                renderResearchStatusCard('Researching...')
                            ) : (
                                <div className="text-sm text-text-muted">
                                    {pendingPlan ? 'Review plan before starting...' : 'Waiting for input...'}
                                </div>
                            )}
                        </div>
                        {pendingPlan && !isLoading && (
                            <div className="p-3 rounded-lg bg-amber-50 border border-amber-200">
                                <div className="text-xs font-medium text-amber-700 mb-2 uppercase tracking-wider">
                                    Plan Ready
                                </div>
                                <div className="text-sm text-amber-900">
                                    A research plan has been created. Review and approve it to start the research.
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Plan Approval Modal */}
            {pendingPlan && (
                <PlanApprovalModal
                    isOpen={!!pendingPlan}
                    plan={pendingPlan.plan}
                    sessionId={pendingPlan.sessionId}
                    onApprove={handlePlanApprove}
                    onCancel={handlePlanCancel}
                />
            )}
        </div>
    )
}
