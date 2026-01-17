import { Button } from "@/components/ui/button"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Mail, Shield, Key, LogOut, Camera } from "lucide-react"
import { useState } from "react"
import { Separator } from "@/components/ui/separator"
import { useAuthStore } from "@/store/auth-store"
import { useNavigate } from "react-router-dom"

interface UserProfileProps {
    open: boolean
    onOpenChange: (open: boolean) => void
}

export function UserProfile({ open, onOpenChange }: UserProfileProps) {
    const { user, logout } = useAuthStore()
    const navigate = useNavigate()

    const [name, setName] = useState(user?.full_name || "Test User")
    const [username, setUsername] = useState(user?.username || "@test")
    const [email, setEmail] = useState(user?.email || "test@example.com")

    const [showChangeEmail, setShowChangeEmail] = useState(false)
    const [showChangePassword, setShowChangePassword] = useState(false)
    const [showPrivacySettings, setShowPrivacySettings] = useState(false)

    const [newEmail, setNewEmail] = useState("")
    const [currentPassword, setCurrentPassword] = useState("")
    const [newPassword, setNewPassword] = useState("")
    const [confirmPassword, setConfirmPassword] = useState("")

    const handleSaveChanges = () => {
        // Save name and username changes
        console.log("Saving profile changes:", { name, username })
        onOpenChange(false)
    }

    const handleChangeEmail = () => {
        // Validate and change email
        if (newEmail && newEmail !== email) {
            setEmail(newEmail)
            setNewEmail("")
            setShowChangeEmail(false)
        }
    }

    const handleChangePassword = () => {
        // Validate and change password
        if (currentPassword && newPassword && newPassword === confirmPassword) {
            console.log("Password changed successfully")
            setCurrentPassword("")
            setNewPassword("")
            setConfirmPassword("")
            setShowChangePassword(false)
        }
    }

    const handleLogout = () => {
        logout()
        onOpenChange(false)
        navigate('/login')
    }

    return (
        <>
            {/* Main Profile Dialog */}
            <Dialog open={open && !showChangeEmail && !showChangePassword && !showPrivacySettings} onOpenChange={onOpenChange}>
                <DialogContent className="sm:max-w-[500px] bg-white rounded-xl max-h-[90vh] flex flex-col">
                    <DialogHeader>
                        <DialogTitle className="text-2xl">User Profile</DialogTitle>
                        <DialogDescription>
                            Manage your account settings and preferences.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="flex-1 overflow-y-auto px-1">
                        <div className="flex flex-col items-center gap-4 py-4">
                            <div className="relative group">
                                <Avatar className="h-24 w-24 border-4 border-primary/10 shadow-lg">
                                    <AvatarImage src="/user-avatar.png" />
                                    <AvatarFallback className="bg-primary text-white text-2xl font-bold">
                                        {name.split(' ').map(n => n[0]).join('')}
                                    </AvatarFallback>
                                </Avatar>
                                <button className="absolute bottom-0 right-0 h-8 w-8 bg-primary rounded-full border-2 border-white shadow-md flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-primary-hover">
                                    <Camera className="h-4 w-4 text-white" />
                                </button>
                                <div className="absolute -bottom-1 -right-1 h-6 w-6 bg-emerald-500 rounded-full border-2 border-white shadow-sm" />
                            </div>
                            <div className="text-center">
                                <h3 className="font-bold text-xl text-text-primary">{name}</h3>
                                <p className="text-sm text-text-muted">{email}</p>
                                <div className="mt-2 inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary">
                                    Pro Plan
                                </div>
                            </div>
                        </div>

                        <Separator />

                        <div className="grid gap-4 py-4">
                            <div className="grid gap-2">
                                <Label htmlFor="name" className="text-sm font-medium">
                                    Full Name
                                </Label>
                                <Input
                                    id="name"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    className="rounded-lg"
                                />
                            </div>
                            <div className="grid gap-2">
                                <Label htmlFor="username" className="text-sm font-medium">
                                    Username
                                </Label>
                                <Input
                                    id="username"
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    className="rounded-lg"
                                />
                            </div>
                        </div>

                        <Separator />

                        <div className="flex flex-col gap-2 py-2">
                            <Button
                                variant="ghost"
                                className="justify-start rounded-lg hover:bg-surface"
                                onClick={() => setShowChangeEmail(true)}
                            >
                                <Mail className="mr-2 h-4 w-4" /> Change Email
                            </Button>
                            <Button
                                variant="ghost"
                                className="justify-start rounded-lg hover:bg-surface"
                                onClick={() => setShowChangePassword(true)}
                            >
                                <Key className="mr-2 h-4 w-4" /> Change Password
                            </Button>
                            <Button
                                variant="ghost"
                                className="justify-start rounded-lg hover:bg-surface"
                                onClick={() => setShowPrivacySettings(true)}
                            >
                                <Shield className="mr-2 h-4 w-4" /> Privacy Settings
                            </Button>
                            <Separator className="my-2" />
                            <Button
                                variant="ghost"
                                className="justify-start text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg"
                                onClick={handleLogout}
                            >
                                <LogOut className="mr-2 h-4 w-4" /> Log Out
                            </Button>
                        </div>
                    </div>

                    <DialogFooter className="mt-2">
                        <Button variant="outline" onClick={() => onOpenChange(false)} className="rounded-lg">
                            Cancel
                        </Button>
                        <Button onClick={handleSaveChanges} className="bg-primary hover:bg-primary-hover text-white rounded-lg">
                            Save Changes
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Change Email Dialog */}
            <Dialog open={showChangeEmail} onOpenChange={setShowChangeEmail}>
                <DialogContent className="sm:max-w-[425px] bg-white rounded-xl">
                    <DialogHeader>
                        <DialogTitle>Change Email</DialogTitle>
                        <DialogDescription>
                            Enter your new email address. You'll need to verify it.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="grid gap-2">
                            <Label htmlFor="current-email">Current Email</Label>
                            <Input
                                id="current-email"
                                value={email}
                                disabled
                                className="rounded-lg bg-surface"
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="new-email">New Email</Label>
                            <Input
                                id="new-email"
                                type="email"
                                placeholder="new.email@example.com"
                                value={newEmail}
                                onChange={(e) => setNewEmail(e.target.value)}
                                className="rounded-lg"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowChangeEmail(false)} className="rounded-lg">
                            Cancel
                        </Button>
                        <Button
                            onClick={handleChangeEmail}
                            disabled={!newEmail || newEmail === email}
                            className="bg-primary hover:bg-primary-hover text-white rounded-lg"
                        >
                            Update Email
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Change Password Dialog */}
            <Dialog open={showChangePassword} onOpenChange={setShowChangePassword}>
                <DialogContent className="sm:max-w-[425px] bg-white rounded-xl">
                    <DialogHeader>
                        <DialogTitle>Change Password</DialogTitle>
                        <DialogDescription>
                            Enter your current password and choose a new one.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="grid gap-2">
                            <Label htmlFor="current-password">Current Password</Label>
                            <Input
                                id="current-password"
                                type="password"
                                value={currentPassword}
                                onChange={(e) => setCurrentPassword(e.target.value)}
                                className="rounded-lg"
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="new-password">New Password</Label>
                            <Input
                                id="new-password"
                                type="password"
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                                className="rounded-lg"
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="confirm-password">Confirm New Password</Label>
                            <Input
                                id="confirm-password"
                                type="password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                className="rounded-lg"
                            />
                            {confirmPassword && newPassword !== confirmPassword && (
                                <p className="text-xs text-red-600">Passwords do not match</p>
                            )}
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowChangePassword(false)} className="rounded-lg">
                            Cancel
                        </Button>
                        <Button
                            onClick={handleChangePassword}
                            disabled={!currentPassword || !newPassword || newPassword !== confirmPassword}
                            className="bg-primary hover:bg-primary-hover text-white rounded-lg"
                        >
                            Change Password
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Privacy Settings Dialog */}
            <Dialog open={showPrivacySettings} onOpenChange={setShowPrivacySettings}>
                <DialogContent className="sm:max-w-[500px] bg-white rounded-xl">
                    <DialogHeader>
                        <DialogTitle>Privacy Settings</DialogTitle>
                        <DialogDescription>
                            Manage your privacy and data sharing preferences.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="flex items-center justify-between p-3 rounded-lg border border-border">
                            <div className="flex-1">
                                <h4 className="text-sm font-medium">Profile Visibility</h4>
                                <p className="text-xs text-text-muted mt-1">Control who can see your profile</p>
                            </div>
                            <Button variant="outline" size="sm" className="rounded-lg">
                                Public
                            </Button>
                        </div>
                        <div className="flex items-center justify-between p-3 rounded-lg border border-border">
                            <div className="flex-1">
                                <h4 className="text-sm font-medium">Activity Status</h4>
                                <p className="text-xs text-text-muted mt-1">Show when you're active</p>
                            </div>
                            <Button variant="outline" size="sm" className="rounded-lg">
                                Enabled
                            </Button>
                        </div>
                        <div className="flex items-center justify-between p-3 rounded-lg border border-border">
                            <div className="flex-1">
                                <h4 className="text-sm font-medium">Data Collection</h4>
                                <p className="text-xs text-text-muted mt-1">Allow usage data collection</p>
                            </div>
                            <Button variant="outline" size="sm" className="rounded-lg">
                                Disabled
                            </Button>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button onClick={() => setShowPrivacySettings(false)} className="bg-primary hover:bg-primary-hover text-white rounded-lg">
                            Done
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    )
}
