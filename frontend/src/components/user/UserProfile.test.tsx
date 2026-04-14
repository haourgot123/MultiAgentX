import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { axiosGetMock, navigateMock, toastErrorMock, toastSuccessMock } = vi.hoisted(() => ({
    axiosGetMock: vi.fn(),
    navigateMock: vi.fn(),
    toastErrorMock: vi.fn(),
    toastSuccessMock: vi.fn(),
}))

vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
    return {
        ...actual,
        useNavigate: () => navigateMock,
    }
})

vi.mock('axios', () => ({
    default: {
        get: axiosGetMock,
    },
}))

vi.mock('sonner', () => ({
    toast: {
        error: toastErrorMock,
        success: toastSuccessMock,
    },
}))

import { UserProfile } from '@/components/user/UserProfile'
import { useAuthStore } from '@/store/auth-store'

const resetAuthStore = () => {
    useAuthStore.setState({
        hasHydrated: true,
        isAuthenticated: true,
        user: {
            id: 1,
            username: 'tester',
            fullName: 'Test User',
            email: 'test@example.com',
            dateOfBirth: '',
            roles: ['user'],
            gender: '',
            country: 'VN',
            phoneNumber: '',
        },
        accessToken: 'token',
        refreshToken: 'refresh',
        login: vi.fn().mockResolvedValue(true),
        register: vi.fn().mockResolvedValue(true),
        refresh: vi.fn().mockResolvedValue(true),
        logout: vi.fn().mockResolvedValue(undefined),
        changePassword: vi.fn().mockResolvedValue({ success: true, message: 'ok' }),
        updateProfile: vi.fn().mockResolvedValue({ success: true, message: 'ok' }),
    })
}

describe('UserProfile', () => {
    beforeEach(() => {
        resetAuthStore()
        axiosGetMock.mockReset()
        axiosGetMock.mockResolvedValue({ data: [] })
        navigateMock.mockReset()
        toastErrorMock.mockReset()
        toastSuccessMock.mockReset()
    })

    it('logs out the user and navigates to login', async () => {
        const user = userEvent.setup()
        const logoutMock = vi.fn().mockResolvedValue(undefined)
        const onOpenChange = vi.fn()
        useAuthStore.setState({ logout: logoutMock })

        render(
            <MemoryRouter>
                <UserProfile open onOpenChange={onOpenChange} />
            </MemoryRouter>
        )

        await waitFor(() => expect(axiosGetMock).toHaveBeenCalled())
        await user.click(screen.getByRole('button', { name: /log out/i }))

        expect(logoutMock).toHaveBeenCalledTimes(1)
        expect(onOpenChange).toHaveBeenCalledWith(false)
        expect(navigateMock).toHaveBeenCalledWith('/login')
    })
})