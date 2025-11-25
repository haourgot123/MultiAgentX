import { useEffect, useRef, useState } from "react"
import { useChatStore } from "@/store/chat-store"
import { MessageBubble } from "./MessageBubble"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Send, Paperclip, Image as ImageIcon, Mic, Search, Globe, Aperture, X, Video } from "lucide-react"
import { cn } from "@/lib/utils"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Toggle } from "@/components/ui/toggle"
import { useLocation } from "react-router-dom" // Added import

export function ChatInterface() {
    const location = useLocation() // Added useLocation hook
    const { getCurrentMessages, input, setInput, addMessage, isLoading, setIsLoading } = useChatStore()
    const messages = getCurrentMessages()
    const scrollRef = useRef<HTMLDivElement>(null)

    // Detect if we're in file chat mode
    const isFileChat = location.pathname === '/chat-file' // Added logic to detect chat type

    // Feature Toggles
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
        if (!input.trim()) return

        const userMessage = {
            role: 'user' as const,
            content: input,
        }

        addMessage(userMessage, isFileChat ? 'file' : 'normal') // Modified addMessage call
        setInput("")
        setIsLoading(true)

        // Simulate AI response
        setTimeout(() => {
            let responseContent = `This is a simulated response.`
            if (activeFeatures.deepResearch) responseContent += ` [Deep Research Active]`
            if (activeFeatures.webSearch) responseContent += ` [Web Search Active]`
            if (activeFeatures.genImage) responseContent += ` [Image Generation Active]`

            addMessage({
                role: 'assistant',
                content: responseContent,
            }, isFileChat ? 'file' : 'normal')
            setIsLoading(false)
        }, 1000)
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
                            {isLoading && (
                                <div className="flex w-full gap-4 p-4">
                                    <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center animate-pulse">
                                        <div className="h-4 w-4 bg-primary rounded-full" />
                                    </div>
                                    <div className="flex items-center">
                                        <span className="text-sm text-text-muted">Thinking...</span>
                                    </div>
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
                            placeholder="Ask anything..."
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
                                                className="h-8 px-2 gap-2 data-[state=on]:bg-primary/10 data-[state=on]:text-primary"
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
                                                className="h-8 w-8 p-0 data-[state=on]:bg-primary/10 data-[state=on]:text-primary"
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
                                                className="h-8 w-8 p-0 data-[state=on]:bg-secondary/10 data-[state=on]:text-secondary"
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
                                                className="h-8 w-8 p-0 data-[state=on]:bg-secondary/10 data-[state=on]:text-secondary"
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
                                    disabled={!input.trim() || isLoading}
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
                            <div className="text-sm text-text-primary">Waiting for input...</div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
