import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useChatStore } from "@/store/chat-store"
import {
    MessageSquare,
    FileText,
    FolderOpen,
    User,
    ChevronLeft,
    ChevronRight,
    Aperture,
    ChevronDown,
    ChevronUp,
    Plus,
    MoreVertical,
    Trash2,
    Edit2
} from "lucide-react"
import { Link, useLocation } from "react-router-dom"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
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
import { UserProfile } from "./user/UserProfile"
import { useState, useEffect } from "react"

interface SidebarProps extends React.HTMLAttributes<HTMLDivElement> {
    isCollapsed?: boolean
    toggleCollapse?: () => void
}

export function Sidebar({ className, isCollapsed = false, toggleCollapse }: SidebarProps) {
    const location = useLocation()
    const { setMode, createNewChat, setCurrentChat, getChatSessions, currentChatId, deleteChat, renameChat } = useChatStore()
    const [showUserProfile, setShowUserProfile] = useState(false)
    const [expandedSection, setExpandedSection] = useState<'chat' | 'file' | null>(null)
    const [isCreatingChat, setIsCreatingChat] = useState(false)
    const [renamingChatId, setRenamingChatId] = useState<string | null>(null)
    const [newChatTitle, setNewChatTitle] = useState("")

    // Get chat sessions based on current route
    const isFileChat = location.pathname === '/chat-file'
    const normalSessions = getChatSessions('normal').filter(s => s.messages.length > 0)
    const fileSessions = getChatSessions('file').filter(s => s.messages.length > 0)

    const isActive = (path: string) => location.pathname === path

    // Auto-expand history when navigating to Chat or Chat With File
    useEffect(() => {
        if (isActive('/')) {
            setExpandedSection('chat')
        } else if (isActive('/chat-file')) {
            setExpandedSection('file')
        }
    }, [location.pathname])

    const toggleSection = (section: 'chat' | 'file') => {
        setExpandedSection(expandedSection === section ? null : section)
    }

    const handleNewChat = () => {
        setIsCreatingChat(true)
        // Create chat with appropriate type
        const chatType = isFileChat ? 'file' : 'normal'
        createNewChat(chatType)

        // Auto-expand history when creating new chat
        if (isActive('/')) {
            setExpandedSection('chat')
        } else if (isActive('/chat-file')) {
            setExpandedSection('file')
        }
        setTimeout(() => setIsCreatingChat(false), 500)
    }

    const handleSelectChat = (chatId: string) => {
        setCurrentChat(chatId)
    }

    const handleDeleteChat = (chatId: string) => {
        if (confirm('Are you sure you want to delete this conversation?')) {
            deleteChat(chatId)
        }
    }

    const handleRenameStart = (chatId: string, currentTitle: string) => {
        setRenamingChatId(chatId)
        setNewChatTitle(currentTitle)
    }

    const handleRenameConfirm = () => {
        if (renamingChatId && newChatTitle.trim()) {
            renameChat(renamingChatId, newChatTitle.trim())
            setRenamingChatId(null)
            setNewChatTitle("")
        }
    }

    const handleRenameCancel = () => {
        setRenamingChatId(null)
        setNewChatTitle("")
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

    const NavItem = ({ icon: Icon, label, path, onClick, variant = "ghost" }: any) => {
        const content = (
            <Button
                variant={variant}
                className={cn(
                    "w-full justify-start text-text-secondary hover:text-primary hover:bg-surface transition-all",
                    isCollapsed ? "justify-center px-2" : "px-4",
                    isActive(path) && "bg-primary/10 text-primary font-medium"
                )}
                onClick={onClick}
            >
                <Icon className={cn("h-5 w-5", isCollapsed ? "mr-0" : "mr-3")} />
                {!isCollapsed && <span>{label}</span>}
            </Button>
        )

        if (isCollapsed) {
            return (
                <TooltipProvider>
                    <Tooltip delayDuration={0}>
                        <TooltipTrigger asChild>{content}</TooltipTrigger>
                        <TooltipContent side="right">{label}</TooltipContent>
                    </Tooltip>
                </TooltipProvider>
            )
        }

        return content
    }

    const ChatHistoryItem = ({ session }: { session: any }) => (
        <div
            className={cn(
                "group relative rounded-md hover:bg-surface transition-all",
                currentChatId === session.id && "bg-primary/10"
            )}
        >
            <Button
                variant="ghost"
                className={cn(
                    "w-full justify-start h-auto py-2 px-2 pr-8 hover:bg-transparent",
                    currentChatId === session.id && "text-primary"
                )}
                onClick={() => handleSelectChat(session.id)}
            >
                <div className="flex flex-col items-start w-full">
                    <span className="text-xs font-medium truncate w-full text-left">{session.title}</span>
                    <span className="text-[10px] text-text-muted">{formatDate(session.updatedAt)}</span>
                </div>
            </Button>

            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6 opacity-0 group-hover:opacity-100 text-text-muted hover:text-primary hover:bg-primary/10 transition-all rounded-md"
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
                        onClick={() => handleDeleteChat(session.id)}
                    >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Delete
                    </DropdownMenuItem>
                </DropdownMenuContent>
            </DropdownMenu>
        </div>
    )

    return (
        <div className={cn("h-full bg-white border-r border-border flex flex-col relative transition-all duration-300", className)}>

            {/* Header */}
            <div className={cn("flex items-center h-20 px-4 border-b border-border", isCollapsed ? "justify-center" : "justify-start gap-3")}>
                <div className="h-10 w-10 rounded-xl bg-tech-gradient flex items-center justify-center shadow-md shrink-0">
                    <Aperture className="h-6 w-6 text-white" />
                </div>
                {!isCollapsed && (
                    <div className="flex flex-col">
                        <span className="font-bold text-xl tracking-tight text-primary">
                            MultiAgentX
                        </span>
                        <span className="text-[10px] text-text-muted font-medium uppercase tracking-widest">Enterprise AI</span>
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
                                        onClick={() => setMode('normal')}
                                    >
                                        <MessageSquare className="h-5 w-5 mr-3" />
                                        <span>Chat</span>
                                    </Button>
                                </Link>
                                {!isCollapsed && isActive('/') && (
                                    <>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className={cn("h-8 w-8 text-primary hover:bg-primary/20 rounded-lg", isCreatingChat && "animate-spin-once")}
                                            onClick={handleNewChat}
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
                                        onClick={() => setMode('file')}
                                    >
                                        <FileText className="h-5 w-5 mr-3" />
                                        <span>Chat with File</span>
                                    </Button>
                                </Link>
                                {!isCollapsed && isActive('/chat-file') && (
                                    <>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className={cn("h-8 w-8 text-primary hover:bg-primary/20 rounded-lg", isCreatingChat && "animate-spin-once")}
                                            onClick={handleNewChat}
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

                    {/* File Management */}
                    <Link to="/files">
                        <NavItem icon={FolderOpen} label="File Management" path="/files" variant={isActive('/files') ? 'secondary' : 'ghost'} />
                    </Link>
                </div>
            </ScrollArea>

            {/* Footer Actions */}
            <div className="p-3 border-t border-border space-y-2">
                <Button
                    variant="ghost"
                    className={cn("w-full justify-start text-text-secondary hover:text-primary hover:bg-surface", isCollapsed ? "justify-center px-2" : "px-4")}
                    onClick={() => setShowUserProfile(true)}
                >
                    <User className={cn("h-5 w-5", isCollapsed ? "mr-0" : "mr-3")} />
                    {!isCollapsed && <span>User Profile</span>}
                </Button>

                {toggleCollapse && (
                    <Button variant="ghost" size="icon" className="w-full mt-2 text-text-muted hover:text-primary" onClick={toggleCollapse}>
                        {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
                    </Button>
                )}
            </div>

            <UserProfile open={showUserProfile} onOpenChange={setShowUserProfile} />

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
                                    handleRenameConfirm()
                                }
                            }}
                        />
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={handleRenameCancel} className="rounded-lg">Cancel</Button>
                        <Button className="bg-primary hover:bg-primary-hover text-white rounded-lg" onClick={handleRenameConfirm}>
                            Rename
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    )
}
