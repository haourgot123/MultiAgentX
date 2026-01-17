import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
    id: number
    username: string
    full_name: string
    email: string
}

interface AuthState {
    isAuthenticated: boolean
    user: User | null
    accessToken: string | null
    refreshToken: string | null
    login: (username: string, password: string) => Promise<boolean>
    refresh: () => Promise<boolean>
    logout: () => Promise<void>
}


export const useAuthStore = create<AuthState>()(
    persist(
        (set, get) => ({
            isAuthenticated: false,
            user: null,
            accessToken: null,
            refreshToken: null,
            login: async (username: string, password: string) => {
                try {
                    const response = await fetch("http://localhost:8000/user/login", {
                        method: 'POST',
                        body: JSON.stringify({ username, password }),
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    })
                    if (!response.ok) {
                        throw new Error('Login failed')
                    }
                    const data = await response.json()
                    console.log('Login data:', data)
                    set({ accessToken: data.accessToken, refreshToken: data.refreshToken })
                    set({ isAuthenticated: true, user: data.user })
                    console.log('User:', get().user)
                    console.log('Login successful')
                    return true
                } catch (error) {
                    console.error('Login failed:', error)
                    return false
                }
            },
            refresh: async () => {
                try {
                    const refreshToken = get().refreshToken
                    if (!refreshToken) {
                        throw new Error('No refresh token found')
                    }
                    const response = await fetch("http://localhost:8000/user/refresh", {
                        method: 'POST',
                        body: JSON.stringify({ refresh_token: refreshToken }),
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    })
                    if (!response.ok) {
                        throw new Error('Refresh failed')
                        // logout user
                        get().logout()
                    }
                    const data = await response.json()
                    set({ accessToken: data.accessToken })
                    return true
                } catch (error) {
                    console.error('Refresh failed:', error)
                    get().logout()
                    return false
                }
            },
            logout: async () => {
                console.log('Logging out user')
                try{
                    console.log('User ID:', get().user?.id)
                    const response  = await fetch("http://localhost:8000/user/logout", {
                        method: 'POST',
                        body: JSON.stringify({ id: get().user?.id }),
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    })
                    if (!response.ok) {
                        throw new Error('Logout failed')
                    }
                    console.log('Logout successful')
                    set({ isAuthenticated: false, user: null, accessToken: null, refreshToken: null })
                } catch (error) {
                    console.error('Logout failed:', error)
                }
            }
        }),
        {
            name: 'auth-storage'
        }
    )
)
