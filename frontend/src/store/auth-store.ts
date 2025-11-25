import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
    username: string
    name: string
    email: string
}

interface AuthState {
    isAuthenticated: boolean
    user: User | null
    login: (username: string, password: string) => boolean
    logout: () => void
}

// Mock user credentials
const MOCK_USER = {
    username: 'test',
    password: 'test',
    name: 'Test User',
    email: 'test@example.com'
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set) => ({
            isAuthenticated: false,
            user: null,
            login: (username: string, password: string) => {
                if (username === MOCK_USER.username && password === MOCK_USER.password) {
                    set({
                        isAuthenticated: true,
                        user: {
                            username: MOCK_USER.username,
                            name: MOCK_USER.name,
                            email: MOCK_USER.email
                        }
                    })
                    return true
                }
                return false
            },
            logout: () => {
                set({
                    isAuthenticated: false,
                    user: null
                })
            }
        }),
        {
            name: 'auth-storage'
        }
    )
)
