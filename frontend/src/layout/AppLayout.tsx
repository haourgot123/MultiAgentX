import { Outlet } from "react-router-dom"
import { Sidebar } from "@/components/Sidebar"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { Menu } from "lucide-react"
import { useEffect, useState } from "react"
import { useAuthStore } from "@/store/auth-store"
import { useFileStore } from "@/store/file-store"

const SIDEBAR_WIDTH_KEY = "multiagentx.sidebar.width"
const SIDEBAR_MIN_WIDTH = 240
const SIDEBAR_MAX_WIDTH = 420
const SIDEBAR_COLLAPSED_WIDTH = 64

export default function AppLayout() {
    const [isMobileOpen, setIsMobileOpen] = useState(false)
    const [isCollapsed, setIsCollapsed] = useState(false)
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
    const accessToken = useAuthStore((state) => state.accessToken)
    const connectIngestionSocket = useFileStore((state) => state.connectIngestionSocket)
    const disconnectIngestionSocket = useFileStore((state) => state.disconnectIngestionSocket)

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

            {/* Mobile Sidebar */}
            <div className="md:hidden absolute top-4 left-4 z-50">
                <Sheet open={isMobileOpen} onOpenChange={setIsMobileOpen}>
                    <SheetTrigger asChild>
                        <Button variant="outline" size="icon" className="glass">
                            <Menu className="h-4 w-4" />
                        </Button>
                    </SheetTrigger>
                    <SheetContent side="left" className="p-0 w-64">
                        <Sidebar />
                    </SheetContent>
                </Sheet>
            </div>

            {/* Main Content */}
            <main className="flex-1 overflow-hidden flex flex-col relative">
                <div className="w-full max-w-[1440px] mx-auto h-full flex flex-col">
                    <Outlet />
                </div>
            </main>
        </div>
    )
}
