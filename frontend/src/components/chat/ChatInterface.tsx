import { useEffect, useRef, useState } from "react"
import { useChatStore } from "@/store/chat-store"
import { useFileStore } from "@/store/file-store"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { MessageBubble } from "./MessageBubble"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Send, Paperclip, Image as ImageIcon, Mic, Search, Globe, Aperture, X, Video, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Toggle } from "@/components/ui/toggle"
import { useLocation } from "react-router-dom"
import { toast } from "sonner"
import { PlanApprovalModal } from "./PlanApprovalModal"
import { apiFetch } from "@/lib/api"

export function ChatInterface() {
    const location = useLocation()
    const {
        getCurrentMessages,
        input,
        setInput,
        isLoading,
        statusSteps,
        currentChatId,
        chatSessions,
        pendingPlan,
        researchPhase,
        createNewChat,
        createDeepResearchPlan,
        approveDeepResearchPlan,
        setPendingPlan,
    } = useChatStore()
    const files = useFileStore((state) => state.files)
    const messages = getCurrentMessages()
    const scrollRef = useRef<HTMLDivElement>(null)

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
    const completedFiles = attachedFiles.filter(
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
        (!currentFileSession || attachedFiles.length === 0 || completedFiles.length === 0)
    const fileChatBlockReason = !currentFileSession || attachedFiles.length === 0
        ? 'Attach at least one file to this conversation before chatting.'
        : hasActiveIngestion
            ? 'Ingestion is still running. Wait until at least one file is Completed.'
            : allAttachedFilesFailed
                ? 'All attached files failed ingestion. Upload another file or retry ingestion.'
                : 'At least one attached file must be Completed before chatting.'
    const inputPlaceholder = fileChatBlocked
        ? fileChatBlockReason
        : "Ask anything..."

    const [activeFeatures, setActiveFeatures] = useState({
        deepResearch: false,
        webSearch: false,
        genImage: false,
        videoAnalysis: false
    })

    const toggleFeature = (feature: keyof typeof activeFeatures) => {
        setActiveFeatures(prev => ({ ...prev, [feature]: !prev[feature] }))
    }

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollIntoView({ behavior: "smooth" })
        }
    }, [messages])

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
        
        // Clear previous status steps when starting new message
        useChatStore.setState({ statusSteps: [] })
        
// Optimistically add user message to chat for Deep Research
        if (activeFeatures.deepResearch) {
            let chatId = currentChatId
            if (!chatId) {
                chatId = await createNewChat('normal')
            }
            if (!chatId) return

            // Clear previous status and set loading
            useChatStore.setState({ 
                statusSteps: [], 
                isLoading: true,
            })

            // Add user message to chat immediately (optimistic)
            const optimisticUserMessage = {
                id: Date.now(),
                role: 'user' as const,
                content: prompt,
                timestamp: Date.now(),
            }
            
            useChatStore.setState((state) => ({
                messagesByChat: {
                    ...state.messagesByChat,
                    [chatId as number]: [
                        ...(state.messagesByChat[chatId as number] || []),
                        optimisticUserMessage,
                    ],
                },
            }))

            setInput("")
            
            try {
                // Save user message to database WITHOUT adding to store again (already added optimistically)
                try {
                    const chatIdForMessage = currentChatId || chatId
                    if (chatIdForMessage) {
                        await apiFetch(`/conversations/${chatIdForMessage}/messages`, {
                            method: 'POST',
                            body: JSON.stringify({
                                role: 'user',
                                content: prompt,
                            }),
                        })
                    }
                } catch (saveError) {
                    console.error('Failed to save user message:', saveError)
                    // Continue even if save fails - message is already in UI
                }
                
                // Create research plan - backend will emit status events
                const planRequest = await createDeepResearchPlan(chatId, prompt)
                
                // Show plan approval modal
                setPendingPlan(planRequest)
            } catch (error) {
                toast.error('Failed to create research plan')
                console.error(error)
                setInput(prompt)
            } finally {
                useChatStore.setState({ isLoading: false })
            }
            return
        }

        setInput("")
        
        try {
            // Normal chat flow
            await useChatStore.getState().streamChat(
                userMessage,
                isFileChat ? 'file' : 'normal',
                {
                    is_web_search_enabled: activeFeatures.webSearch,
                    is_deep_research_enabled: activeFeatures.deepResearch,
                    is_generate_image_enabled: activeFeatures.genImage,
                }
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
                    <ScrollArea className="h-full pr-4">
                        <div className="flex flex-col gap-6 pb-4">
                            {messages.length === 0 && (
                                <div className="flex flex-col items-center justify-center h-[60vh] text-center space-y-6">
                                    <div className="h-20 w-20 rounded-3xl bg-tech-gradient flex items-center justify-center shadow-lg animate-in zoom-in duration-500">
                                        <Aperture className="h-10 w-10 text-white" />
                                    </div>
                                    <div className="space-y-2">
                                        <h3 className="text-2xl font-bold tracking-tight text-text-primary">MultiAgentX</h3>
                                        <p className="text-text-muted max-w-sm mx-auto">
                                            Your advanced AI assistant for research, analysis, and creation.
                                        </p>
                                    </div>
                                </div>
                            )}
                            {messages.map((msg) => (
                                <MessageBubble key={msg.id} message={msg} />
                            ))}
                            {/* Deep Research - show current status */}
                            {activeFeatures.deepResearch && isLoading && (
                                <div className="flex items-center gap-3 p-4 animate-in fade-in duration-300">
                                    <div className="flex h-5 w-5 items-center justify-center">
                                        <Loader2 className="h-4 w-4 animate-spin text-primary" />
                                    </div>
                                    <span className="text-sm font-medium text-text-muted">
                                        {researchPhase === 'researching'
                                            ? (statusSteps.length > 0 ? statusSteps[statusSteps.length - 1] : 'Researching...')
                                            : researchPhase === 'planning'
                                                ? 'Creating research plan...'
                                                : (pendingPlan ? 'Review plan before starting...' : 'Processing...')}
                                    </span>
                                </div>
                            )}
                            {/* Show status steps in Chat only when NOT using Deep Research */}
                            {(isLoading || statusSteps.length > 0) && !activeFeatures.deepResearch && (
                                <div className="flex flex-col gap-2 p-4 animate-in fade-in duration-300">
                                    {statusSteps.length > 0 ? (
                                        statusSteps.map((step, idx) => (
                                            <div key={idx} className="flex items-center gap-3">
                                                <div className="flex h-5 w-5 items-center justify-center">
                                                    <Loader2 className="h-4 w-4 animate-spin text-primary" />
                                                </div>
                                                <span className="text-sm font-medium text-text-muted">
                                                    {step}
                                                </span>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="text-sm text-text-muted">
                                            {isLoading && pendingPlan === null ? 'Processing...' : 
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
                            disabled={isLoading || fileChatBlocked}
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

                                {/* Feature Toggles */}
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

                                <TooltipProvider>
                                    <Tooltip>
                                        <TooltipTrigger asChild>
                                            <Toggle
                                                pressed={activeFeatures.videoAnalysis}
                                                onPressedChange={() => toggleFeature('videoAnalysis')}
                                                size="sm"
                                                className={cn(
                                                    "h-8 w-8 p-0",
                                                    activeFeatures.videoAnalysis && "!bg-[#22c55e] !text-white hover:!bg-[#16a34a]"
                                                )}
                                            >
                                                <Video className="h-4 w-4" />
                                            </Toggle>
                                        </TooltipTrigger>
                                        <TooltipContent>Video Analysis</TooltipContent>
                                    </Tooltip>
                                </TooltipProvider>
                            </div>

                            <div className="flex items-center gap-2">
                                <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full">
                                    <Mic className="h-4 w-4" />
                                </Button>
                                <Button
                                    onClick={handleSend}
                                    disabled={!input.trim() || isLoading || fileChatBlocked}
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
            {activeFeatures.deepResearch && (
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
                            {statusSteps.length > 0 ? (
                                <div className="space-y-2">
                                    {statusSteps.map((step, idx) => (
                                        <div key={idx} className="text-sm text-text-primary animate-in fade-in duration-300 flex items-start gap-2">
                                            <Loader2 className="h-4 w-4 animate-spin text-primary mt-0.5 flex-shrink-0" />
                                            <span>{step}</span>
                                        </div>
                                    ))}
                                </div>
                            ) : isLoading && researchPhase === 'planning' ? (
                                <div className="text-sm text-text-muted animate-pulse">
                                    Creating research plan...
                                </div>
                            ) : isLoading && researchPhase === 'researching' ? (
                                <div className="text-sm text-text-muted animate-pulse">
                                    Researching...
                                </div>
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
