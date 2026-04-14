import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { toastErrorMock, toastInfoMock, toastSuccessMock } = vi.hoisted(() => ({
    toastErrorMock: vi.fn(),
    toastInfoMock: vi.fn(),
    toastSuccessMock: vi.fn(),
}))

vi.mock('sonner', () => ({
    toast: {
        error: toastErrorMock,
        info: toastInfoMock,
        success: toastSuccessMock,
    },
}))

vi.mock('@/components/user/UserProfile', () => ({
    UserProfile: () => null,
}))

import { Sidebar } from '@/components/Sidebar'
import { useChatStore } from '@/store/chat-store'

const resetChatStore = () => {
    useChatStore.setState({
        currentChatId: null,
        activeChatIdByType: {
            normal: null,
            file: null,
        },
        chatSessions: [],
        messagesByChat: {},
        fileChatNewRequestId: 0,
        fileChatCitations: {},
        activeCitation: null,
        input: '',
        isLoading: false,
        statusSteps: [],
        mode: 'normal',
        pendingPlan: null,
        researchPhase: 'idle',
        activateChatType: vi.fn(),
        fetchChatSessions: vi.fn().mockResolvedValue([]),
        createNewChat: vi.fn().mockResolvedValue(1),
        setCurrentChat: vi.fn(),
        loadConversation: vi.fn().mockResolvedValue(undefined),
        deleteChat: vi.fn().mockResolvedValue(undefined),
        renameChat: vi.fn().mockResolvedValue(undefined),
        requestFileChatNew: vi.fn(),
    })
}

describe('Sidebar', () => {
    beforeEach(() => {
        resetChatStore()
        toastErrorMock.mockReset()
        toastInfoMock.mockReset()
        toastSuccessMock.mockReset()
    })

    it('loads a selected normal conversation from history', async () => {
        const user = userEvent.setup()
        const setCurrentChatMock = vi.fn()
        const loadConversationMock = vi.fn().mockResolvedValue(undefined)

        useChatStore.setState({
            chatSessions: [
                {
                    id: 9,
                    title: 'Research thread',
                    createdAt: Date.parse('2026-04-15T10:00:00Z'),
                    updatedAt: Date.parse('2026-04-15T10:10:00Z'),
                    chatType: 'normal',
                    fileIds: [],
                    messageCount: 3,
                },
            ],
            setCurrentChat: setCurrentChatMock,
            loadConversation: loadConversationMock,
            fetchChatSessions: vi.fn().mockResolvedValue([]),
        })

        render(
            <MemoryRouter initialEntries={['/']}>
                <Sidebar />
            </MemoryRouter>
        )

        await user.click(screen.getByText('Research thread'))

        expect(setCurrentChatMock).toHaveBeenCalledWith(9)
        expect(loadConversationMock).toHaveBeenCalledWith(9)
    })

    it('switches to normal chat context when clicking the chat icon from file chat', async () => {
        const user = userEvent.setup()
        const activateChatTypeMock = vi.fn()

        useChatStore.setState({
            currentChatId: 21,
            activeChatIdByType: {
                normal: null,
                file: 21,
            },
            activateChatType: activateChatTypeMock,
            fetchChatSessions: vi.fn().mockResolvedValue([]),
        })

        render(
            <MemoryRouter initialEntries={['/chat-file']}>
                <Sidebar />
            </MemoryRouter>
        )

        await user.click(screen.getByText('Chat'))

        expect(activateChatTypeMock).toHaveBeenCalledWith('normal')
    })

    it('switches to file chat context when clicking the file chat icon from normal chat', async () => {
        const user = userEvent.setup()
        const activateChatTypeMock = vi.fn()

        useChatStore.setState({
            currentChatId: 9,
            activeChatIdByType: {
                normal: 9,
                file: 21,
            },
            activateChatType: activateChatTypeMock,
            fetchChatSessions: vi.fn().mockResolvedValue([]),
        })

        render(
            <MemoryRouter initialEntries={['/']}>
                <Sidebar />
            </MemoryRouter>
        )

        activateChatTypeMock.mockClear()
        await user.click(screen.getByText('Chat with File'))

        expect(activateChatTypeMock).toHaveBeenCalledWith('file')
    })

    it('requests a fresh file chat from the file route', async () => {
        const user = userEvent.setup()
        const requestFileChatNewMock = vi.fn()
        const setCurrentChatMock = vi.fn()

        useChatStore.setState({
            requestFileChatNew: requestFileChatNewMock,
            setCurrentChat: setCurrentChatMock,
            fetchChatSessions: vi.fn().mockResolvedValue([]),
        })

        const { container } = render(
            <MemoryRouter initialEntries={['/chat-file']}>
                <Sidebar />
            </MemoryRouter>
        )

        const fileChatLabel = screen.getByText('Chat with File')
        const fileChatRow = fileChatLabel.closest('a')?.parentElement
        const rowButtons = fileChatRow?.querySelectorAll('button') ?? container.querySelectorAll('button')
        const newFileChatButton = rowButtons[1] as HTMLButtonElement

        await user.click(newFileChatButton)

        expect(setCurrentChatMock).toHaveBeenCalledWith(null, 'file')
        expect(requestFileChatNewMock).toHaveBeenCalledTimes(1)
        expect(toastInfoMock).toHaveBeenCalledWith('Upload file to start a new file conversation')
    })
})