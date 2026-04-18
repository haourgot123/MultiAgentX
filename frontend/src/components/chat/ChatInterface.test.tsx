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
        loadingChatId: null,
        conversationOpenScrollBehavior: null,
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
                    sasUrl: null,
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
                    sasUrl: null,
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

    it('jumps to the last turn immediately when opening a conversation', () => {
        const scrollIntoViewMock = vi.fn()
        const originalScrollIntoView = HTMLElement.prototype.scrollIntoView
        HTMLElement.prototype.scrollIntoView = scrollIntoViewMock

        useChatStore.setState({
            currentChatId: 15,
            chatSessions: [
                {
                    id: 15,
                    title: 'Existing Chat',
                    createdAt: Date.parse('2026-04-15T10:00:00Z'),
                    updatedAt: Date.parse('2026-04-15T10:05:00Z'),
                    chatType: 'normal',
                    fileIds: [],
                    messageCount: 2,
                },
            ],
            messagesByChat: {
                15: [
                    {
                        id: 1,
                        role: 'user',
                        content: 'First question',
                        timestamp: Date.parse('2026-04-15T10:00:00Z'),
                    },
                    {
                        id: 2,
                        role: 'assistant',
                        content: 'Latest answer',
                        timestamp: Date.parse('2026-04-15T10:05:00Z'),
                    },
                ],
            },
        })

        render(
            <MemoryRouter initialEntries={['/']}>
                <ChatInterface />
            </MemoryRouter>
        )

        expect(scrollIntoViewMock).toHaveBeenCalledWith({
            behavior: 'auto',
            block: 'end',
        })

        HTMLElement.prototype.scrollIntoView = originalScrollIntoView
    })

    it('smoothly scrolls to the last turn when a conversation is opened from the sidebar', () => {
        const scrollIntoViewMock = vi.fn()
        const originalScrollIntoView = HTMLElement.prototype.scrollIntoView
        HTMLElement.prototype.scrollIntoView = scrollIntoViewMock

        useChatStore.setState({
            currentChatId: 17,
            conversationOpenScrollBehavior: 'smooth',
            chatSessions: [
                {
                    id: 17,
                    title: 'Sidebar Chat',
                    createdAt: Date.parse('2026-04-15T10:00:00Z'),
                    updatedAt: Date.parse('2026-04-15T10:05:00Z'),
                    chatType: 'normal',
                    fileIds: [],
                    messageCount: 2,
                },
            ],
            messagesByChat: {
                17: [
                    {
                        id: 1,
                        role: 'user',
                        content: 'Open this conversation',
                        timestamp: Date.parse('2026-04-15T10:00:00Z'),
                    },
                    {
                        id: 2,
                        role: 'assistant',
                        content: 'Most recent turn',
                        timestamp: Date.parse('2026-04-15T10:05:00Z'),
                    },
                ],
            },
        })

        render(
            <MemoryRouter initialEntries={['/']}>
                <ChatInterface />
            </MemoryRouter>
        )

        expect(scrollIntoViewMock).toHaveBeenCalledWith({
            behavior: 'smooth',
            block: 'end',
        })
        expect(useChatStore.getState().conversationOpenScrollBehavior).toBeNull()

        HTMLElement.prototype.scrollIntoView = originalScrollIntoView
    })

    it('clears stale smooth scroll behavior after leaving chat so re-enter jumps immediately', () => {
        const scrollIntoViewMock = vi.fn()
        const originalScrollIntoView = HTMLElement.prototype.scrollIntoView
        HTMLElement.prototype.scrollIntoView = scrollIntoViewMock

        useChatStore.setState({
            currentChatId: 18,
            conversationOpenScrollBehavior: 'smooth',
            chatSessions: [
                {
                    id: 18,
                    title: 'Return Chat',
                    createdAt: Date.parse('2026-04-15T10:00:00Z'),
                    updatedAt: Date.parse('2026-04-15T10:05:00Z'),
                    chatType: 'normal',
                    fileIds: [],
                    messageCount: 2,
                },
            ],
            messagesByChat: {
                18: [
                    {
                        id: 1,
                        role: 'user',
                        content: 'Open this conversation',
                        timestamp: Date.parse('2026-04-15T10:00:00Z'),
                    },
                    {
                        id: 2,
                        role: 'assistant',
                        content: 'Most recent turn',
                        timestamp: Date.parse('2026-04-15T10:05:00Z'),
                    },
                ],
            },
        })

        const firstRender = render(
            <MemoryRouter initialEntries={['/']}>
                <ChatInterface />
            </MemoryRouter>
        )

        firstRender.unmount()
        expect(useChatStore.getState().conversationOpenScrollBehavior).toBeNull()

        scrollIntoViewMock.mockClear()

        render(
            <MemoryRouter initialEntries={['/']}>
                <ChatInterface />
            </MemoryRouter>
        )

        expect(scrollIntoViewMock).toHaveBeenLastCalledWith({
            behavior: 'auto',
            block: 'end',
        })

        HTMLElement.prototype.scrollIntoView = originalScrollIntoView
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

    it('does not auto-scroll while the assistant is streaming even if the user is near the bottom', () => {
        const scrollIntoViewMock = vi.fn()
        const originalScrollIntoView = HTMLElement.prototype.scrollIntoView
        HTMLElement.prototype.scrollIntoView = scrollIntoViewMock

        useChatStore.setState({
            currentChatId: 16,
            chatSessions: [
                {
                    id: 16,
                    title: 'Streaming Chat',
                    createdAt: Date.parse('2026-04-15T10:00:00Z'),
                    updatedAt: Date.parse('2026-04-15T10:00:00Z'),
                    chatType: 'normal',
                    fileIds: [],
                    messageCount: 2,
                },
            ],
            messagesByChat: {
                16: [
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
            value: 760,
        })

        fireEvent.scroll(viewport)
        scrollIntoViewMock.mockClear()

        act(() => {
            useChatStore.setState({
                isLoading: true,
                loadingChatId: 16,
                messagesByChat: {
                    16: [
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

    it('does not show Processing while a file-chat assistant message is already streaming', () => {
        useChatStore.setState({
            currentChatId: 18,
            loadingChatId: 18,
            isLoading: true,
            statusSteps: [],
            chatSessions: [
                {
                    id: 18,
                    title: 'File Chat Streaming',
                    createdAt: Date.parse('2026-04-15T10:00:00Z'),
                    updatedAt: Date.parse('2026-04-15T10:00:00Z'),
                    chatType: 'file',
                    fileIds: [52],
                    messageCount: 2,
                },
            ],
            messagesByChat: {
                18: [
                    {
                        id: 1,
                        role: 'user',
                        content: 'Summarize this file',
                        timestamp: Date.parse('2026-04-15T10:00:00Z'),
                    },
                    {
                        id: 2,
                        role: 'assistant',
                        content: 'This document describes',
                        timestamp: Date.parse('2026-04-15T10:00:01Z'),
                    },
                ],
            },
        })

        useFileStore.setState({
            files: [
                {
                    id: 52,
                    name: 'ready.pdf',
                    type: 'application/pdf',
                    size: 1024,
                    uploadedAt: Date.parse('2026-04-15T10:00:00Z'),
                    sasUrl: null,
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

        render(
            <MemoryRouter initialEntries={['/chat-file']}>
                <ChatInterface />
            </MemoryRouter>
        )

        expect(screen.getByText('This document describes')).toBeInTheDocument()
        expect(screen.queryByText('Processing...')).not.toBeInTheDocument()
    })

    it('shows only the latest progress steps instead of the full status list', () => {
        useChatStore.setState({
            currentChatId: 19,
            loadingChatId: 19,
            isLoading: true,
            statusSteps: [
                'Optimizing query for document search...',
                'Optimized query ...',
                'Searching documents with multiple queries...',
                'Found relevant passages ...',
                'Organizing retrieved passages with citations...',
                'Evaluating relevance of retrieved passages ...',
                'Context is relevant. Generating answer...',
            ],
            chatSessions: [
                {
                    id: 19,
                    title: 'Progress Chat',
                    createdAt: Date.parse('2026-04-15T10:00:00Z'),
                    updatedAt: Date.parse('2026-04-15T10:00:00Z'),
                    chatType: 'normal',
                    fileIds: [],
                    messageCount: 1,
                },
            ],
            messagesByChat: {
                19: [
                    {
                        id: 1,
                        role: 'user',
                        content: 'Summarize these files',
                        timestamp: Date.parse('2026-04-15T10:00:00Z'),
                    },
                ],
            },
        })

        render(
            <MemoryRouter initialEntries={['/']}>
                <ChatInterface />
            </MemoryRouter>
        )

        expect(screen.queryByText('Optimizing query for document search...')).not.toBeInTheDocument()
        expect(screen.queryByText('Found relevant passages ...')).not.toBeInTheDocument()
        expect(screen.getByText('Organizing retrieved passages with citations...')).toBeInTheDocument()
        expect(screen.getByText('Evaluating relevance of retrieved passages ...')).toBeInTheDocument()
        expect(screen.getByText('Context is relevant. Generating answer...')).toBeInTheDocument()
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
                is_web_search_enabled: true,
                is_deep_research_enabled: false,
                is_generate_image_enabled: true,
                route_preference: 'auto',
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
