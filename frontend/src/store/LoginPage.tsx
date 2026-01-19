import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Aperture } from "lucide-react"
import { Link, useNavigate } from "react-router-dom"
import { useState } from "react"
import { useAuthStore } from "@/store/auth-store"
import { toast } from "sonner"
export default function LoginPage() {
    const navigate = useNavigate()
    const login = useAuthStore((state) => state.login)
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')

        const success = await login(username, password)

        if (success) {
            toast.success('Login successful')
            setTimeout(() => {
                navigate("/", { replace: true })
              }, 100)
        } else {
            toast.error('Invalid username or password')
            setError('Invalid username or password')
        }
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary/5 via-white to-primary/10 p-4">
            <Card className="w-full max-w-md shadow-2xl border-border rounded-2xl">
                <CardHeader className="space-y-4 pb-8">
                    <div className="flex justify-center">
                        <div className="h-16 w-16 rounded-2xl bg-tech-gradient flex items-center justify-center shadow-lg">
                            <Aperture className="h-10 w-10 text-white" />
                        </div>
                    </div>
                    <div className="text-center space-y-2">
                        <CardTitle className="text-3xl font-bold text-primary">Welcome Back</CardTitle>
                        <CardDescription className="text-base">
                            MultiAgentX Enterprise AI
                        </CardDescription>
                    </div>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div className="space-y-2">
                            <Label htmlFor="username" className="text-sm font-medium">Username</Label>
                            <Input
                                id="username"
                                type="text"
                                placeholder="Enter your username"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                className="h-11 rounded-lg"
                                required
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="password" className="text-sm font-medium">Password</Label>
                            <Input
                                id="password"
                                type="password"
                                placeholder="Enter your password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="h-11 rounded-lg"
                                required
                            />
                        </div>

                        {error && (
                            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                                {error}
                            </div>
                        )}

                        {/* <div className="bg-primary/5 border border-primary/20 p-4 rounded-lg">
                            <p className="text-xs font-medium text-primary mb-1">Demo Credentials:</p>
                            <p className="text-xs text-text-muted">Username: <span className="font-mono font-semibold">test</span></p>
                            <p className="text-xs text-text-muted">Password: <span className="font-mono font-semibold">test</span></p>
                        </div> */}

                        <Button
                            type="submit"
                            className="w-full h-11 bg-primary hover:bg-primary-hover text-white font-medium rounded-lg shadow-md hover:shadow-lg transition-all"
                        >
                            Sign In
                        </Button>
                        <div className="text-center text-sm text-muted-foreground">
                            Don&apos;t have an account?{" "}
                            <Link
                                to="/register"
                                className="text-primary font-medium hover:underline"
                            >
                                Sign up
                            </Link>
                        </div>
                    </form>
                </CardContent>
            </Card>
        </div>
    )
}
