import { render, screen } from '@testing-library/react'
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