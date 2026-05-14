import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useChatStore } from "@/store/chat-store"
import { useAuthStore } from "@/store/auth-store"
import { useAgentSkillsStore } from "@/store/agent-skills-store"
import {
    MessageSquare,
    ChevronLeft,
    ChevronRight,
    Aperture,
    ChevronDown,
    ChevronUp,
    Plus,
    MoreVertical,
    Trash2,
    Edit2,
    ScanSearch,
    Bot,
} from "lucide-react"
import { Link, useLocation } from "react-router-dom"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
    DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { useState, useEffect } from "react"
import { toast } from "sonner"

interface SidebarProps extends React.HTMLAttributes<HTMLDivElement> {
    isCollapsed?: boolean
    toggleCollapse?: () => void
}

export function Sidebar({ className, isCollapsed = false, toggleCollapse }: SidebarProps) {
    const location = useLocation()
    const {
        activateChatType,
        createNewChat,
        setCurrentChat,
        setConversationOpenScrollBehavior,
        getChatSessions,
        fetchChatSessions,
        loadConversation,
        currentChatId,
        deleteChat,
        renameChat,
        requestFileChatNew
    } = useChatStore()
    const {
        conversations: skillConversations,
        currentConversationId,
        fetchConversations: fetchSkillConversations,
        loadConversation: loadSkillConversation,
        createConversation: createSkillConversation,
        renameConversation: renameSkillConversation,
        deleteConversation: deleteSkillConversation,
    } = useAgentSkillsStore()
    const [expandedSection, setExpandedSection] = useState<'chat' | 'file' | 'skills' | null>(null)
    const [isCreatingChat, setIsCreatingChat] = useState(false)
    const [isCreatingSkillConversation, setIsCreatingSkillConversation] = useState(false)
    const [renamingChatId, setRenamingChatId] = useState<number | null>(null)
    const [newChatTitle, setNewChatTitle] = useState("")
    const [deletingChatId, setDeletingChatId] = useState<number | null>(null)
    const [deletingChatTitle, setDeletingChatTitle] = useState("")
    const [renamingSkillConversationId, setRenamingSkillConversationId] = useState<number | null>(null)
    const [newSkillConversationTitle, setNewSkillConversationTitle] = useState("")
    const [deletingSkillConversationId, setDeletingSkillConversationId] = useState<number | null>(null)
    const [deletingSkillConversationTitle, setDeletingSkillConversationTitle] = useState("")

    // Get chat sessions based on current route
    const isFileChat = location.pathname === '/chat-file'
    const normalSessions = getChatSessions('normal')
    const fileSessions = getChatSessions('file')

    const isActive = (path: string) => location.pathname === path

    // Auto-expand history when navigating to Chat or Chat With File
    useEffect(() => {
        if (isActive('/')) {
            activateChatType('normal')
            setExpandedSection('chat')
        } else if (isActive('/chat-file')) {
            activateChatType('file')
            setExpandedSection('file')
        } else if (isActive('/agent-skills')) {
            setExpandedSection('skills')
        }
    }, [location.pathname, activateChatType])

    useEffect(() => {
        const loadSessions = async () => {
            try {
                await Promise.all([
                    fetchChatSessions('normal'),
                    fetchChatSessions('file'),
                    fetchSkillConversations(),
                ])
            } catch (error) {
                if (!useAuthStore.getState().isAuthenticated) return
                toast.error(
                    error instanceof Error ? error.message : 'Failed to load conversations'
                )
            }
        }
        void loadSessions()
    }, [fetchChatSessions, fetchSkillConversations])

    const toggleSection = (section: 'chat' | 'file' | 'skills') => {
        setExpandedSection(expandedSection === section ? null : section)
    }

    const handleNewChat = async () => {
        if (isFileChat) {
            setCurrentChat(null, 'file')
            requestFileChatNew()
            setExpandedSection('file')
            toast.info('Upload file to start a new file conversation')
            return
        }

        setIsCreatingChat(true)
        try {
            await createNewChat('normal')

            if (isActive('/')) {
                setExpandedSection('chat')
            }
            toast.success('Created new conversation')
        } catch (error) {
            toast.error(
                error instanceof Error ? error.message : 'Failed to create conversation'
            )
        } finally {
            setIsCreatingChat(false)
        }
    }

    const handleNewSkillConversation = async () => {
        setIsCreatingSkillConversation(true)
        try {
            const conversationId = await createSkillConversation()
            await fetchSkillConversations()
            await loadSkillConversation(conversationId)
            setExpandedSection('skills')
            toast.success('Created new Agent Skills conversation')
        } catch (error) {
            toast.error(
                error instanceof Error ? error.message : 'Failed to create Agent Skills conversation'
            )
        } finally {
            setIsCreatingSkillConversation(false)
        }
    }

    const handleSelectSkillConversation = async (conversationId: number) => {
        try {
            await loadSkillConversation(conversationId)
        } catch (error) {
            toast.error(
                error instanceof Error ? error.message : 'Failed to load Agent Skills conversation'
            )
        }
    }

    const handleSelectChat = async (chatId: number) => {
        try {
            setConversationOpenScrollBehavior('smooth')
            setCurrentChat(chatId)
            await loadConversation(chatId)
        } catch (error) {
            toast.error(
                error instanceof Error ? error.message : 'Failed to load conversation'
            )
        }
    }

    const handleDeleteChat = (chatId: number, chatTitle: string) => {
        setDeletingChatId(chatId)
        setDeletingChatTitle(chatTitle)
    }

    const handleDeleteConfirm = async () => {
        if (!deletingChatId) return

        try {
            await deleteChat(deletingChatId)
            toast.success('Conversation deleted')
        } catch (error) {
            toast.error(
                error instanceof Error ? error.message : 'Failed to delete conversation'
            )
        } finally {
            setDeletingChatId(null)
            setDeletingChatTitle("")
        }
    }

    const handleDeleteCancel = () => {
        setDeletingChatId(null)
        setDeletingChatTitle("")
    }

    const handleRenameStart = (chatId: number, currentTitle: string) => {
        setRenamingChatId(chatId)
        setNewChatTitle(currentTitle)
    }

    const handleRenameConfirm = async () => {
        if (renamingChatId && newChatTitle.trim()) {
            try {
                await renameChat(renamingChatId, newChatTitle.trim())
                setRenamingChatId(null)
                setNewChatTitle("")
                toast.success('Conversation renamed')
            } catch (error) {
                toast.error(
                    error instanceof Error ? error.message : 'Failed to rename conversation'
                )
            }
        }
    }

    const handleRenameCancel = () => {
        setRenamingChatId(null)
        setNewChatTitle("")
    }

    const handleRenameSkillStart = (conversationId: number, currentTitle: string) => {
        setRenamingSkillConversationId(conversationId)
        setNewSkillConversationTitle(currentTitle)
    }

    const handleRenameSkillCancel = () => {
        setRenamingSkillConversationId(null)
        setNewSkillConversationTitle("")
    }

    const handleRenameSkillConfirm = async () => {
        if (renamingSkillConversationId && newSkillConversationTitle.trim()) {
            try {
                await renameSkillConversation(renamingSkillConversationId, newSkillConversationTitle.trim())
                await fetchSkillConversations()
                setRenamingSkillConversationId(null)
                setNewSkillConversationTitle("")
                toast.success('Agent Skills conversation renamed')
            } catch (error) {
                toast.error(
                    error instanceof Error ? error.message : 'Failed to rename Agent Skills conversation'
                )
            }
        }
    }

    const handleDeleteSkillConversation = (conversationId: number, conversationTitle: string) => {
        setDeletingSkillConversationId(conversationId)
        setDeletingSkillConversationTitle(conversationTitle)
    }

    const handleDeleteSkillCancel = () => {
        setDeletingSkillConversationId(null)
        setDeletingSkillConversationTitle("")
    }

    const handleDeleteSkillConfirm = async () => {
        if (!deletingSkillConversationId) return

        try {
            await deleteSkillConversation(deletingSkillConversationId)
            await fetchSkillConversations()
            toast.success('Agent Skills conversation deleted')
        } catch (error) {
            toast.error(
                error instanceof Error ? error.message : 'Failed to delete Agent Skills conversation'
            )
        } finally {
            setDeletingSkillConversationId(null)
            setDeletingSkillConversationTitle("")
        }
    }

    const formatDate = (timestamp: number) => {
        const now = Date.now()
        const diff = now - timestamp
        const hours = Math.floor(diff / (1000 * 60 * 60))
        const days = Math.floor(diff / (1000 * 60 * 60 * 24))

        if (hours < 1) return 'Just now'
        if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`
        if (days === 1) return 'Yesterday'
        if (days < 7) return `${days} days ago`
        return new Date(timestamp).toLocaleDateString()
    }

    const ChatHistoryItem = ({ session }: { session: any }) => (
        <div
            className={cn(
                "group grid grid-cols-[1fr_auto] items-center gap-1 rounded-md hover:bg-surface transition-all",
                currentChatId === session.id && "bg-primary/10"
            )}
        >
            <Button
                variant="ghost"
                className={cn(
                    "min-w-0 justify-start h-auto py-2 px-2 hover:bg-transparent overflow-hidden",
                    currentChatId === session.id && "text-primary"
                )}
                onClick={() => void handleSelectChat(session.id)}
            >
                <div className="flex flex-col items-start min-w-0 w-full">
                    <span
                        className="text-xs font-medium truncate w-full text-left"
                        title={session.title}
                    >
                        {session.title}
                    </span>
                    <span className="text-[10px] text-text-muted">{formatDate(session.updatedAt)}</span>
                </div>
            </Button>

            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button
                        variant="ghost"
                        size="icon"
                        className={cn(
                            "h-7 w-7 mr-1 shrink-0 text-text-muted hover:text-primary hover:bg-primary/10 transition-all rounded-md",
                            "opacity-100"
                        )}
                        onClick={(e) => e.stopPropagation()}
                    >
                        <MoreVertical className="h-3 w-3" />
                    </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="bg-white border-border shadow-lg rounded-lg">
                    <DropdownMenuItem
                        className="cursor-pointer rounded-md"
                        onClick={() => handleRenameStart(session.id, session.title)}
                    >
                        <Edit2 className="mr-2 h-4 w-4" />
                        Rename
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                        className="text-red-600 focus:text-red-600 cursor-pointer rounded-md"
                        onClick={() => handleDeleteChat(session.id, session.title)}
                    >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Delete
                    </DropdownMenuItem>
                </DropdownMenuContent>
            </DropdownMenu>
        </div>
    )

    const SkillHistoryItem = ({ conversation }: { conversation: { id: number; title: string; updatedAt: number } }) => (
        <div
            className={cn(
                "group grid grid-cols-[1fr_auto] items-center gap-1 rounded-md hover:bg-surface transition-all",
                currentConversationId === conversation.id && "bg-primary/10"
            )}
        >
            <Button
                variant="ghost"
                className={cn(
                    "min-w-0 justify-start h-auto py-2 px-2 hover:bg-transparent overflow-hidden",
                    currentConversationId === conversation.id && "text-primary"
                )}
                onClick={() => void handleSelectSkillConversation(conversation.id)}
            >
                <div className="flex flex-col items-start min-w-0 w-full">
                    <span className="text-xs font-medium truncate w-full text-left" title={conversation.title}>
                        {conversation.title}
                    </span>
                    <span className="text-[10px] text-text-muted">{formatDate(conversation.updatedAt)}</span>
                </div>
            </Button>

            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 mr-1 shrink-0 rounded-md text-text-muted hover:text-primary hover:bg-primary/10 transition-all"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <MoreVertical className="h-3 w-3" />
                    </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="bg-white border-border shadow-lg rounded-lg">
                    <DropdownMenuItem
                        className="cursor-pointer rounded-md"
                        onClick={() => handleRenameSkillStart(conversation.id, conversation.title)}
                    >
                        <Edit2 className="mr-2 h-4 w-4" />
                        Rename
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                        className="text-red-600 focus:text-red-600 cursor-pointer rounded-md"
                        onClick={() => handleDeleteSkillConversation(conversation.id, conversation.title)}
                    >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Delete
                    </DropdownMenuItem>
                </DropdownMenuContent>
            </DropdownMenu>
        </div>
    )

    return (
        <div className={cn("h-full border-r border-border/80 bg-[linear-gradient(180deg,rgba(255,255,255,0.94),rgba(243,247,241,0.92))] flex flex-col relative transition-all duration-300", className)}>

            {/* Header */}
            <div className={cn("flex items-center h-20 px-4 border-b border-border/80", isCollapsed ? "justify-center" : "justify-start gap-3")}>
                <div className="h-10 w-10 rounded-[1.1rem] bg-tech-gradient flex items-center justify-center shadow-[0_16px_30px_rgba(18,130,79,0.26)] shrink-0 ring-1 ring-emerald-500/20">
                    <Aperture className="h-6 w-6 text-white" />
                </div>
                {!isCollapsed && (
                    <div className="flex flex-col">
                        <span className="font-display font-bold text-xl tracking-tight text-primary">
                            MultiAgentX
                        </span>
                        <span className="text-[10px] text-text-muted font-medium uppercase tracking-[0.24em]">Signal Engine</span>
                    </div>
                )}
            </div>

            {/* Main Navigation */}
            <ScrollArea className="flex-1 py-6">
                <div className="px-3 space-y-2">
                    {/* Chat Section */}
                    <div>
                        {/* Full-width highlight container */}
                        <div className={cn(
                            "rounded-lg transition-all",
                            isActive('/') && "bg-primary/10"
                        )}>
                            <div className="flex items-center gap-1 px-2 py-1">
                                <Link to="/" className="flex-1">
                                    <Button
                                        variant="ghost"
                                        className={cn(
                                            "w-full justify-start text-text-secondary hover:text-primary hover:bg-transparent transition-all px-2",
                                            isActive('/') && "text-primary font-medium"
                                        )}
                                        onClick={() => activateChatType('normal')}
                                    >
                                        <span className="icon-tech-shell mr-3 flex h-8 w-8 items-center justify-center rounded-xl">
                                            <MessageSquare className="h-4 w-4" />
                                        </span>
                                        <span>Chat</span>
                                    </Button>
                                </Link>
                                {!isCollapsed && isActive('/') && (
                                    <>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className={cn("h-8 w-8 text-primary hover:bg-primary/20 rounded-lg", isCreatingChat && "animate-spin-once")}
                                            onClick={() => void handleNewChat()}
                                        >
                                            <Plus className="h-4 w-4" />
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-8 w-8 text-primary hover:bg-primary/20 rounded-lg"
                                            onClick={() => toggleSection('chat')}
                                        >
                                            {expandedSection === 'chat' ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                                        </Button>
                                    </>
                                )}
                            </div>
                        </div>

                        {/* Chat History - Expandable with smooth animation */}
                        {!isCollapsed && isActive('/') && expandedSection === 'chat' && (
                            <div className="overflow-hidden animate-expand">
                                <div className="ml-4 mt-2 space-y-1 border-l-2 border-border pl-3">
                                    {normalSessions.length === 0 ? (
                                        <div className="text-xs text-text-muted py-2 px-2">No chat history</div>
                                    ) : (
                                        normalSessions.map((session) => (
                                            <ChatHistoryItem key={session.id} session={session} />
                                        ))
                                    )}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Chat with File Section */}
                    <div>
                        {/* Full-width highlight container */}
                        <div className={cn(
                            "rounded-lg transition-all",
                            isActive('/chat-file') && "bg-primary/10"
                        )}>
                            <div className="flex items-center gap-1 px-2 py-1">
                                <Link to="/chat-file" className="flex-1">
                                    <Button
                                        variant="ghost"
                                        className={cn(
                                            "w-full justify-start text-text-secondary hover:text-primary hover:bg-transparent transition-all px-2",
                                            isActive('/chat-file') && "text-primary font-medium"
                                        )}
                                        onClick={() => activateChatType('file')}
                                    >
                                        <span className="icon-tech-shell mr-3 flex h-8 w-8 items-center justify-center rounded-xl">
                                            <ScanSearch className="h-4 w-4" />
                                        </span>
                                        <span>Chat with File</span>
                                    </Button>
                                </Link>
                                {!isCollapsed && isActive('/chat-file') && (
                                    <>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className={cn("h-8 w-8 text-primary hover:bg-primary/20 rounded-lg", isCreatingChat && "animate-spin-once")}
                                            onClick={() => void handleNewChat()}
                                        >
                                            <Plus className="h-4 w-4" />
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-8 w-8 text-primary hover:bg-primary/20 rounded-lg"
                                            onClick={() => toggleSection('file')}
                                        >
                                            {expandedSection === 'file' ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                                        </Button>
                                    </>
                                )}
                            </div>
                        </div>

                        {/* File Chat History - Expandable with smooth animation */}
                        {!isCollapsed && isActive('/chat-file') && expandedSection === 'file' && (
                            <div className="overflow-hidden animate-expand">
                                <div className="ml-4 mt-2 space-y-1 border-l-2 border-border pl-3">
                                    {fileSessions.length === 0 ? (
                                        <div className="text-xs text-text-muted py-2 px-2">No chat history</div>
                                    ) : (
                                        fileSessions.map((session) => (
                                            <ChatHistoryItem key={session.id} session={session} />
                                        ))
                                    )}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Agent Skills Section */}
                    <div>
                        <div className={cn(
                            "rounded-lg transition-all",
                            isActive('/agent-skills') && "bg-primary/10"
                        )}>
                            <div className="flex items-center gap-1 px-2 py-1">
                                <Link to="/agent-skills" className="flex-1">
                                    <Button
                                        variant="ghost"
                                        className={cn(
                                            "w-full justify-start text-text-secondary hover:text-primary hover:bg-transparent transition-all px-2",
                                            isActive('/agent-skills') && "text-primary font-medium"
                                        )}
                                    >
                                        <span className="icon-tech-shell mr-3 flex h-8 w-8 items-center justify-center rounded-xl">
                                            <Bot className="h-4 w-4" />
                                        </span>
                                        <span>Agent Skills</span>
                                    </Button>
                                </Link>
                                {!isCollapsed && isActive('/agent-skills') && (
                                    <>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className={cn(
                                                "h-8 w-8 rounded-lg text-primary hover:bg-primary/20",
                                                isCreatingSkillConversation && "animate-spin-once"
                                            )}
                                            onClick={() => void handleNewSkillConversation()}
                                        >
                                            <Plus className="h-4 w-4" />
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-8 w-8 text-primary hover:bg-primary/20 rounded-lg"
                                            onClick={() => toggleSection('skills')}
                                        >
                                            {expandedSection === 'skills' ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                                        </Button>
                                    </>
                                )}
                            </div>
                        </div>

                        {!isCollapsed && isActive('/agent-skills') && expandedSection === 'skills' && (
                            <div className="overflow-hidden animate-expand">
                                <div className="ml-4 mt-2 space-y-1 border-l-2 border-border pl-3">
                                    {skillConversations.length === 0 ? (
                                        <div className="text-xs text-text-muted py-2 px-2">No Agent Skills history</div>
                                    ) : (
                                        skillConversations.map((conversation) => (
                                            <SkillHistoryItem key={conversation.id} conversation={conversation} />
                                        ))
                                    )}
                                </div>
                            </div>
                        )}
                    </div>

                </div>
            </ScrollArea>

            {/* Footer Actions */}
            <div className="p-3 border-t border-border space-y-2">
                {toggleCollapse && (
                    <Button variant="ghost" size="icon" className="w-full mt-2 text-text-muted hover:text-primary" onClick={toggleCollapse}>
                        {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
                    </Button>
                )}
            </div>

            {/* Rename Dialog */}
            <Dialog open={renamingChatId !== null} onOpenChange={(open) => !open && handleRenameCancel()}>
                <DialogContent className="bg-white rounded-xl">
                    <DialogHeader>
                        <DialogTitle>Rename Conversation</DialogTitle>
                        <DialogDescription>Enter a new name for this conversation</DialogDescription>
                    </DialogHeader>
                    <div className="py-4">
                        <Label htmlFor="chat-title">Conversation Name</Label>
                        <Input
                            id="chat-title"
                            value={newChatTitle}
                            onChange={(e) => setNewChatTitle(e.target.value)}
                            className="mt-2 rounded-lg"
                            onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                    void handleRenameConfirm()
                                }
                            }}
                        />
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={handleRenameCancel} className="rounded-lg">Cancel</Button>
                        <Button
                            className="bg-primary hover:bg-primary-hover text-white rounded-lg"
                            onClick={() => void handleRenameConfirm()}
                        >
                            Rename
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Delete Confirmation Dialog */}
            <Dialog open={deletingChatId !== null} onOpenChange={(open) => !open && handleDeleteCancel()}>
                <DialogContent className="bg-white rounded-xl">
                    <DialogHeader>
                        <DialogTitle>Delete Conversation</DialogTitle>
                        <DialogDescription>
                            Are you sure you want to delete
                            {deletingChatTitle ? ` "${deletingChatTitle}"` : " this conversation"}?
                            This action cannot be undone.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button variant="outline" onClick={handleDeleteCancel} className="rounded-lg">Cancel</Button>
                        <Button
                            variant="destructive"
                            className="rounded-lg"
                            onClick={() => void handleDeleteConfirm()}
                        >
                            Delete
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Dialog open={renamingSkillConversationId !== null} onOpenChange={(open) => !open && handleRenameSkillCancel()}>
                <DialogContent className="bg-white rounded-xl">
                    <DialogHeader>
                        <DialogTitle>Rename Agent Skills Conversation</DialogTitle>
                        <DialogDescription>Enter a new name for this Agent Skills conversation</DialogDescription>
                    </DialogHeader>
                    <div className="py-4">
                        <Label htmlFor="skill-conversation-title">Conversation Name</Label>
                        <Input
                            id="skill-conversation-title"
                            value={newSkillConversationTitle}
                            onChange={(e) => setNewSkillConversationTitle(e.target.value)}
                            className="mt-2 rounded-lg"
                            onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                    void handleRenameSkillConfirm()
                                }
                            }}
                        />
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={handleRenameSkillCancel} className="rounded-lg">Cancel</Button>
                        <Button
                            className="bg-primary hover:bg-primary-hover text-white rounded-lg"
                            onClick={() => void handleRenameSkillConfirm()}
                        >
                            Rename
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Dialog open={deletingSkillConversationId !== null} onOpenChange={(open) => !open && handleDeleteSkillCancel()}>
                <DialogContent className="bg-white rounded-xl">
                    <DialogHeader>
                        <DialogTitle>Delete Agent Skills Conversation</DialogTitle>
                        <DialogDescription>
                            Are you sure you want to delete
                            {deletingSkillConversationTitle ? ` "${deletingSkillConversationTitle}"` : " this conversation"}?
                            This action cannot be undone.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button variant="outline" onClick={handleDeleteSkillCancel} className="rounded-lg">Cancel</Button>
                        <Button
                            variant="destructive"
                            className="rounded-lg"
                            onClick={() => void handleDeleteSkillConfirm()}
                        >
                            Delete
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    )
}
