import { Link, Outlet, useLocation } from "react-router-dom"
import { Sidebar } from "@/components/Sidebar"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { Menu, FolderOpen, LogOut, User } from "lucide-react"
import { useEffect, useState } from "react"
import { useAuthStore } from "@/store/auth-store"
import { useFileStore } from "@/store/file-store"
import { UserProfile } from "@/components/user/UserProfile"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

const SIDEBAR_WIDTH_KEY = "multiagentx.sidebar.width"
const SIDEBAR_MIN_WIDTH = 240
const SIDEBAR_MAX_WIDTH = 420
const SIDEBAR_COLLAPSED_WIDTH = 64

export default function AppLayout() {
    const location = useLocation()
    const [isMobileOpen, setIsMobileOpen] = useState(false)
    const [isCollapsed, setIsCollapsed] = useState(false)
    const [showUserProfile, setShowUserProfile] = useState(false)
    const [sidebarWidth, setSidebarWidth] = useState(() => {
        if (typeof window === "undefined") {
            return 288
        }

        const savedWidth = Number(window.localStorage.getItem(SIDEBAR_WIDTH_KEY))
        if (Number.isFinite(savedWidth)) {
            return Math.min(Math.max(savedWidth, SIDEBAR_MIN_WIDTH), SIDEBAR_MAX_WIDTH)
        }

        return 288
    })
    const [isResizing, setIsResizing] = useState(false)
    const user = useAuthStore((state) => state.user)
    const accessToken = useAuthStore((state) => state.accessToken)
    const logout = useAuthStore((state) => state.logout)
    const connectIngestionSocket = useFileStore((state) => state.connectIngestionSocket)
    const disconnectIngestionSocket = useFileStore((state) => state.disconnectIngestionSocket)

    const handleLogout = async () => {
        try {
            await logout()
            toast.success('Logged out')
        } catch (error) {
            toast.error(error instanceof Error ? error.message : 'Logout failed')
        }
    }

    useEffect(() => {
        if (!accessToken) {
            disconnectIngestionSocket()
            return
        }
        connectIngestionSocket()
        return () => {
            disconnectIngestionSocket()
        }
    }, [accessToken, connectIngestionSocket, disconnectIngestionSocket])

    useEffect(() => {
        if (typeof window === "undefined") {
            return
        }

        window.localStorage.setItem(SIDEBAR_WIDTH_KEY, String(sidebarWidth))
    }, [sidebarWidth])

    useEffect(() => {
        if (!isResizing) {
            return
        }

        const handleMouseMove = (event: MouseEvent) => {
            const nextWidth = Math.min(
                Math.max(event.clientX, SIDEBAR_MIN_WIDTH),
                SIDEBAR_MAX_WIDTH
            )
            setSidebarWidth(nextWidth)
        }

        const handleMouseUp = () => {
            setIsResizing(false)
        }

        document.body.style.userSelect = "none"
        document.body.style.cursor = "col-resize"
        window.addEventListener("mousemove", handleMouseMove)
        window.addEventListener("mouseup", handleMouseUp)

        return () => {
            document.body.style.userSelect = ""
            document.body.style.cursor = ""
            window.removeEventListener("mousemove", handleMouseMove)
            window.removeEventListener("mouseup", handleMouseUp)
        }
    }, [isResizing])

    return (
        <div className="flex h-screen overflow-hidden bg-background">
            {/* Desktop Sidebar */}
            <div
                className="relative hidden md:block flex-shrink-0 transition-[width] duration-300 ease-in-out"
                style={{ width: isCollapsed ? SIDEBAR_COLLAPSED_WIDTH : sidebarWidth }}
            >
                <Sidebar
                    isCollapsed={isCollapsed}
                    toggleCollapse={() => setIsCollapsed(!isCollapsed)}
                />
                {!isCollapsed && (
                    <button
                        type="button"
                        aria-label="Resize sidebar"
                        aria-orientation="vertical"
                        onMouseDown={() => setIsResizing(true)}
                        className="absolute inset-y-0 -right-1 z-20 hidden w-2 cursor-col-resize bg-transparent transition-colors hover:bg-primary/20 md:block"
                    >
                        <span className="absolute inset-y-8 left-1/2 w-px -translate-x-1/2 bg-border/80" />
                    </button>
                )}
            </div>

            {/* Main Content */}
            <main className="flex-1 overflow-hidden flex flex-col relative">
                <div className="w-full max-w-[1440px] mx-auto h-full flex flex-col">
                    <header className="h-16 border-b border-slate-200 bg-white px-4 md:px-6 shrink-0 text-foreground shadow-[0_8px_24px_rgba(15,23,19,0.04)]">
                        <div className="h-full flex items-center justify-between gap-4">
                            <div className="flex items-center gap-3">
                                <div className="md:hidden">
                                    <Sheet open={isMobileOpen} onOpenChange={setIsMobileOpen}>
                                        <SheetTrigger asChild>
                                            <Button variant="outline" size="icon" className="border-emerald-200 bg-white/80 text-emerald-950 shadow-sm hover:bg-emerald-50 hover:text-emerald-950">
                                                <Menu className="h-4 w-4" />
                                            </Button>
                                        </SheetTrigger>
                                        <SheetContent side="left" className="p-0 w-64">
                                            <Sidebar />
                                        </SheetContent>
                                    </Sheet>
                                </div>

                                <Link to="/files">
                                    <Button
                                        variant="ghost"
                                        className={cn(
                                            "gap-2 rounded-xl border border-transparent px-3 text-slate-700 hover:border-emerald-200 hover:bg-emerald-50/70 hover:text-slate-950",
                                            location.pathname === '/files' && "border-emerald-200 bg-emerald-50/80 text-slate-950 shadow-sm"
                                        )}
                                    >
                                        <span className="icon-tech-shell flex h-7 w-7 items-center justify-center rounded-lg">
                                            <FolderOpen className="h-4 w-4" />
                                        </span>
                                        <span>File Management</span>
                                    </Button>
                                </Link>
                            </div>

                            <div className="flex items-center gap-2">
                                <Button
                                    variant="ghost"
                                    className="gap-2 rounded-xl border border-transparent px-3 text-slate-700 hover:border-emerald-200 hover:bg-emerald-50/70 hover:text-slate-950"
                                    onClick={() => setShowUserProfile(true)}
                                >
                                    <span className="icon-tech-shell flex h-7 w-7 items-center justify-center rounded-lg">
                                        <User className="h-4 w-4" />
                                    </span>
                                    <span className="hidden sm:inline">{user?.fullName || user?.username || 'User'}</span>
                                </Button>
                                <Button
                                    variant="ghost"
                                    className="gap-2 rounded-xl border border-transparent px-3 text-slate-700 hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700"
                                    onClick={() => void handleLogout()}
                                >
                                    <span className="icon-tech-shell flex h-7 w-7 items-center justify-center rounded-lg">
                                        <LogOut className="h-4 w-4" />
                                    </span>
                                    <span className="hidden sm:inline">Logout</span>
                                </Button>
                            </div>
                        </div>
                    </header>

                    <div className="flex-1 overflow-hidden">
                        <Outlet />
                    </div>
                </div>
            </main>

            <UserProfile open={showUserProfile} onOpenChange={setShowUserProfile} />
        </div>
    )
}
