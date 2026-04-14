import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { toastErrorMock, toastSuccessMock, toastInfoMock } = vi.hoisted(() => ({
    toastErrorMock: vi.fn(),
    toastSuccessMock: vi.fn(),
    toastInfoMock: vi.fn(),
}))

vi.mock('sonner', () => ({
    toast: {
        error: toastErrorMock,
        success: toastSuccessMock,
        info: toastInfoMock,
    },
}))

import { ChatInterface } from '@/components/chat/ChatInterface'
import { useChatStore } from '@/store/chat-store'
import { useFileStore } from '@/store/file-store'

const resetStores = () => {
    useChatStore.setState({
        currentChatId: null,
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
    })
    useFileStore.setState({
        files: [],
        isLoading: false,
        isUploading: false,
    })
}

describe('ChatInterface', () => {
    beforeEach(() => {
        resetStores()
        toastErrorMock.mockReset()
        toastSuccessMock.mockReset()
        toastInfoMock.mockReset()
    })

    it('renders messages in chronological order even if state is unsorted', () => {
        useChatStore.setState({
            currentChatId: 1,
            chatSessions: [
                {
                    id: 1,
                    title: 'Chat',
                    createdAt: Date.parse('2026-04-15T10:00:00Z'),
                    updatedAt: Date.parse('2026-04-15T10:02:00Z'),
                    chatType: 'normal',
                    fileIds: [],
                    messageCount: 2,
                },
            ],
            messagesByChat: {
                1: [
                    {
                        id: 2,
                        role: 'assistant',
                        content: 'Pipeline process of PP-OCRv5',
                        timestamp: Date.parse('2026-04-15T10:02:00Z'),
                    },
                    {
                        id: 1,
                        role: 'user',
                        content: 'What is Paddle OCR',
                        timestamp: Date.parse('2026-04-15T10:01:00Z'),
                    },
                ],
            },
        })

        render(
            <MemoryRouter initialEntries={['/']}>
                <ChatInterface />
            </MemoryRouter>
        )

        const userMessage = screen.getByText('What is Paddle OCR')
        const assistantMessage = screen.getByText('Pipeline process of PP-OCRv5')

        expect(
            userMessage.compareDocumentPosition(assistantMessage) & Node.DOCUMENT_POSITION_FOLLOWING
        ).toBeTruthy()
    })

    it('blocks file chat input when no completed file is attached', () => {
        useChatStore.setState({
            currentChatId: 9,
            chatSessions: [
                {
                    id: 9,
                    title: 'File Chat',
                    createdAt: Date.parse('2026-04-15T10:00:00Z'),
                    updatedAt: Date.parse('2026-04-15T10:00:00Z'),
                    chatType: 'file',
                    fileIds: [50],
                    messageCount: 0,
                },
            ],
            messagesByChat: { 9: [] },
        })

        useFileStore.setState({
            files: [
                {
                    id: 50,
                    name: 'ocr.pdf',
                    type: 'application/pdf',
                    size: 2048,
                    uploadedAt: Date.parse('2026-04-15T10:00:00Z'),
                    storagePath: 'tmp/ocr.pdf',
                    ingestionStatus: 'processing',
                    ingestionError: null,
                    ingestedChunks: 0,
                    ingestedAt: null,
                    ingestionStage: 'embedding',
                    ingestionProgress: 40,
                },
            ],
            isLoading: false,
            isUploading: false,
        })

        render(
            <MemoryRouter initialEntries={['/chat-file']}>
                <ChatInterface />
            </MemoryRouter>
        )

        const input = screen.getByPlaceholderText(
            'Ingestion is still running. Wait until at least one file is Completed.'
        )

        expect(input).toBeDisabled()
        expect(
            screen.getByText('Ingestion is still running. Wait until at least one file is Completed.')
        ).toBeInTheDocument()
    })

    it('hides auxiliary action buttons in file chat mode', () => {
        useChatStore.setState({
            currentChatId: 10,
            chatSessions: [
                {
                    id: 10,
                    title: 'File Chat',
                    createdAt: Date.parse('2026-04-15T10:00:00Z'),
                    updatedAt: Date.parse('2026-04-15T10:00:00Z'),
                    chatType: 'file',
                    fileIds: [51],
                    messageCount: 0,
                },
            ],
            messagesByChat: { 10: [] },
        })

        useFileStore.setState({
            files: [
                {
                    id: 51,
                    name: 'ready.pdf',
                    type: 'application/pdf',
                    size: 1024,
                    uploadedAt: Date.parse('2026-04-15T10:00:00Z'),
                    storagePath: 'tmp/ready.pdf',
                    ingestionStatus: 'completed',
                    ingestionError: null,
                    ingestedChunks: 5,
                    ingestedAt: Date.parse('2026-04-15T10:05:00Z'),
                    ingestionStage: 'completed',
                    ingestionProgress: 100,
                },
            ],
            isLoading: false,
            isUploading: false,
        })

        const { container } = render(
            <MemoryRouter initialEntries={['/chat-file']}>
                <ChatInterface />
            </MemoryRouter>
        )

        expect(screen.queryByText('Deep Research')).not.toBeInTheDocument()
        expect(container.querySelectorAll('button')).toHaveLength(1)
    })

    it('reloads the active conversation on mount when messages are missing after refresh', async () => {
        const loadConversationMock = vi
            .spyOn(useChatStore.getState(), 'loadConversation')
            .mockResolvedValue(undefined)

        useChatStore.setState({
            currentChatId: 13,
            chatSessions: [
                {
                    id: 13,
                    title: 'Persisted Chat',
                    createdAt: Date.parse('2026-04-15T10:00:00Z'),
                    updatedAt: Date.parse('2026-04-15T10:00:00Z'),
                    chatType: 'normal',
                    fileIds: [],
                    messageCount: 2,
                },
            ],
            messagesByChat: {},
        })

        render(
            <MemoryRouter initialEntries={['/']}>
                <ChatInterface />
            </MemoryRouter>
        )

        await waitFor(() => {
            expect(loadConversationMock).toHaveBeenCalledWith(13)
        })

        loadConversationMock.mockRestore()
    })

    it('stops auto-scrolling while streaming when the user scrolls up', async () => {
        const scrollIntoViewMock = vi.fn()
        const originalScrollIntoView = HTMLElement.prototype.scrollIntoView
        HTMLElement.prototype.scrollIntoView = scrollIntoViewMock

        useChatStore.setState({
            currentChatId: 14,
            chatSessions: [
                {
                    id: 14,
                    title: 'Streaming Chat',
                    createdAt: Date.parse('2026-04-15T10:00:00Z'),
                    updatedAt: Date.parse('2026-04-15T10:00:00Z'),
                    chatType: 'normal',
                    fileIds: [],
                    messageCount: 2,
                },
            ],
            messagesByChat: {
                14: [
                    {
                        id: 1,
                        role: 'user',
                        content: 'Tell me more',
                        timestamp: Date.parse('2026-04-15T10:00:00Z'),
                    },
                    {
                        id: 2,
                        role: 'assistant',
                        content: 'Initial answer',
                        timestamp: Date.parse('2026-04-15T10:00:01Z'),
                    },
                ],
            },
        })

        const { container } = render(
            <MemoryRouter initialEntries={['/']}>
                <ChatInterface />
            </MemoryRouter>
        )

        const viewport = container.querySelector('[data-radix-scroll-area-viewport]') as HTMLDivElement

        Object.defineProperty(viewport, 'scrollHeight', {
            configurable: true,
            value: 1200,
        })
        Object.defineProperty(viewport, 'clientHeight', {
            configurable: true,
            value: 400,
        })
        Object.defineProperty(viewport, 'scrollTop', {
            configurable: true,
            writable: true,
            value: 680,
        })

        fireEvent.scroll(viewport)
        scrollIntoViewMock.mockClear()

        act(() => {
            useChatStore.setState({
                messagesByChat: {
                    14: [
                        {
                            id: 1,
                            role: 'user',
                            content: 'Tell me more',
                            timestamp: Date.parse('2026-04-15T10:00:00Z'),
                        },
                        {
                            id: 2,
                            role: 'assistant',
                            content: 'Initial answer with more streamed tokens',
                            timestamp: Date.parse('2026-04-15T10:00:01Z'),
                        },
                    ],
                },
            })
        })

        expect(scrollIntoViewMock).not.toHaveBeenCalled()
        HTMLElement.prototype.scrollIntoView = originalScrollIntoView
    })

    it('sends a normal chat message through the store', async () => {
        const user = userEvent.setup()
        const streamChatMock = vi
            .spyOn(useChatStore.getState(), 'streamChat')
            .mockResolvedValue(undefined)

        useChatStore.setState({
            currentChatId: 11,
            chatSessions: [
                {
                    id: 11,
                    title: 'Chat',
                    createdAt: Date.parse('2026-04-15T10:00:00Z'),
                    updatedAt: Date.parse('2026-04-15T10:00:00Z'),
                    chatType: 'normal',
                    fileIds: [],
                    messageCount: 0,
                },
            ],
            messagesByChat: { 11: [] },
        })

        const { container } = render(
            <MemoryRouter initialEntries={['/']}>
                <ChatInterface />
            </MemoryRouter>
        )

        const input = screen.getByPlaceholderText('Ask anything...')
        await user.type(input, 'What is PaddleOCR?')

        const buttons = container.querySelectorAll('button')
        const sendButton = buttons[buttons.length - 1] as HTMLButtonElement
        await user.click(sendButton)

        expect(streamChatMock).toHaveBeenCalledWith(
            {
                role: 'user',
                content: 'What is PaddleOCR?',
            },
            'normal',
            {
                is_web_search_enabled: false,
                is_deep_research_enabled: false,
                is_generate_image_enabled: false,
            }
        )
        expect(input).toHaveValue('')

        streamChatMock.mockRestore()
    })

    it('restores the input and shows an error toast when send fails', async () => {
        const user = userEvent.setup()
        const streamChatMock = vi
            .spyOn(useChatStore.getState(), 'streamChat')
            .mockRejectedValue(new Error('send failed'))

        useChatStore.setState({
            currentChatId: 12,
            chatSessions: [
                {
                    id: 12,
                    title: 'Chat',
                    createdAt: Date.parse('2026-04-15T10:00:00Z'),
                    updatedAt: Date.parse('2026-04-15T10:00:00Z'),
                    chatType: 'normal',
                    fileIds: [],
                    messageCount: 0,
                },
            ],
            messagesByChat: { 12: [] },
        })

        const { container } = render(
            <MemoryRouter initialEntries={['/']}>
                <ChatInterface />
            </MemoryRouter>
        )

        const input = screen.getByPlaceholderText('Ask anything...')
        await user.type(input, 'Pipeline process of PP-OCRv5')

        const buttons = container.querySelectorAll('button')
        const sendButton = buttons[buttons.length - 1] as HTMLButtonElement
        await user.click(sendButton)

        expect(toastErrorMock).toHaveBeenCalledWith('Failed to send message')
        expect(input).toHaveValue('Pipeline process of PP-OCRv5')

        streamChatMock.mockRestore()
    })
})