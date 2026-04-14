import { beforeEach, describe, expect, it, vi } from 'vitest'

const { apiFetchMock, apiFetchStreamMock } = vi.hoisted(() => ({
    apiFetchMock: vi.fn(),
    apiFetchStreamMock: vi.fn(),
}))

vi.mock('@/lib/api', () => ({
    apiFetch: apiFetchMock,
    apiFetchStream: apiFetchStreamMock,
}))

import { useChatStore } from '@/store/chat-store'

const resetStore = () => {
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
    })
}

describe('useChatStore', () => {
    beforeEach(() => {
        apiFetchMock.mockReset()
        apiFetchStreamMock.mockReset()
        resetStore()
    })

    it('sorts loaded conversation messages by timestamp', async () => {
        apiFetchMock.mockResolvedValueOnce({
            id: 42,
            title: 'OCR Chat',
            chat_type: 'normal',
            file_ids: [],
            message_count: 2,
            created_at: '2026-04-15T10:00:00Z',
            updated_at: '2026-04-15T10:00:02Z',
            messages: [
                {
                    id: 2,
                    role: 'assistant',
                    content: 'Pipeline process...',
                    created_at: '2026-04-15T10:00:02Z',
                    updated_at: '2026-04-15T10:00:02Z',
                },
                {
                    id: 1,
                    role: 'user',
                    content: 'What is PaddleOCR?',
                    created_at: '2026-04-15T10:00:01Z',
                    updated_at: '2026-04-15T10:00:01Z',
                },
            ],
        })

        await useChatStore.getState().loadConversation(42)
        useChatStore.getState().setCurrentChat(42)

        expect(useChatStore.getState().getCurrentMessages().map((message) => message.id)).toEqual([1, 2])
        expect(useChatStore.getState().getCurrentMessages().map((message) => message.role)).toEqual([
            'user',
            'assistant',
        ])
    })

    it('switches active conversation by chat type without reusing file chat in normal mode', () => {
        useChatStore.setState({
            currentChatId: 7,
            activeChatIdByType: {
                normal: 3,
                file: 7,
            },
            chatSessions: [
                {
                    id: 3,
                    title: 'Normal Chat',
                    createdAt: Date.parse('2026-04-15T09:00:00Z'),
                    updatedAt: Date.parse('2026-04-15T09:10:00Z'),
                    chatType: 'normal',
                    fileIds: [],
                    messageCount: 2,
                },
                {
                    id: 7,
                    title: 'File Chat',
                    createdAt: Date.parse('2026-04-15T10:00:00Z'),
                    updatedAt: Date.parse('2026-04-15T10:10:00Z'),
                    chatType: 'file',
                    fileIds: [99],
                    messageCount: 4,
                },
            ],
            messagesByChat: {
                3: [
                    {
                        id: 30,
                        role: 'user',
                        content: 'Normal thread',
                        timestamp: Date.now(),
                    },
                ],
                7: [
                    {
                        id: 70,
                        role: 'user',
                        content: 'File thread',
                        timestamp: Date.now(),
                    },
                ],
            },
        })

        useChatStore.getState().activateChatType('normal')

        expect(useChatStore.getState().currentChatId).toBe(3)
        expect(useChatStore.getState().getCurrentMessages().map((message) => message.id)).toEqual([30])
    })

    it('stores citations and reloads conversation after successful file chat streaming', async () => {
        useChatStore.setState({
            currentChatId: 7,
            activeChatIdByType: {
                normal: null,
                file: 7,
            },
            messagesByChat: { 7: [] },
        })

        apiFetchStreamMock.mockImplementationOnce(async (_path, _options, onEvent) => {
            onEvent({ event: 'status', data: { message: 'Searching files...' } })
            onEvent({ event: 'token', data: { delta: 'Answer' } })
            onEvent({ event: 'token', data: { delta: ' found' } })
            onEvent({
                event: 'done',
                data: {
                    citations: [
                        {
                            citation_label: '1.1',
                            file_id: 99,
                            file_name: 'ocr.pdf',
                            page_no: 3,
                            chunk_index: 0,
                        },
                    ],
                },
            })
        })

        apiFetchMock.mockResolvedValueOnce({
            id: 7,
            title: 'File Chat',
            chat_type: 'file',
            file_ids: [99],
            message_count: 2,
            created_at: '2026-04-15T10:00:00Z',
            updated_at: '2026-04-15T10:00:03Z',
            messages: [
                {
                    id: 100,
                    role: 'user',
                    content: 'Explain this file',
                    created_at: '2026-04-15T10:00:01Z',
                    updated_at: '2026-04-15T10:00:01Z',
                },
                {
                    id: 101,
                    role: 'assistant',
                    content: 'Answer found',
                    created_at: '2026-04-15T10:00:02Z',
                    updated_at: '2026-04-15T10:00:02Z',
                },
            ],
        })

        await useChatStore.getState().streamChat(
            { role: 'user', content: 'Explain this file' },
            'file'
        )

        expect(apiFetchStreamMock).toHaveBeenCalledTimes(1)
        expect(useChatStore.getState().messagesByChat[7].map((message) => message.id)).toEqual([100, 101])
        expect(useChatStore.getState().fileChatCitations[7]).toEqual([
            {
                citation_label: '1.1',
                file_id: 99,
                file_name: 'ocr.pdf',
                page_no: 3,
                chunk_index: 0,
            },
        ])
        expect(useChatStore.getState().isLoading).toBe(false)
        expect(useChatStore.getState().statusSteps).toEqual([])
    })

    it('uses the remembered normal conversation for normal chat when current chat is a file conversation', async () => {
        useChatStore.setState({
            currentChatId: 7,
            activeChatIdByType: {
                normal: 3,
                file: 7,
            },
            chatSessions: [
                {
                    id: 3,
                    title: 'Normal Chat',
                    createdAt: Date.parse('2026-04-15T09:00:00Z'),
                    updatedAt: Date.parse('2026-04-15T09:10:00Z'),
                    chatType: 'normal',
                    fileIds: [],
                    messageCount: 0,
                },
                {
                    id: 7,
                    title: 'File Chat',
                    createdAt: Date.parse('2026-04-15T10:00:00Z'),
                    updatedAt: Date.parse('2026-04-15T10:10:00Z'),
                    chatType: 'file',
                    fileIds: [99],
                    messageCount: 1,
                },
            ],
            messagesByChat: {
                3: [],
                7: [
                    {
                        id: 70,
                        role: 'user',
                        content: 'File thread',
                        timestamp: Date.now(),
                    },
                ],
            },
        })

        apiFetchStreamMock.mockImplementationOnce(async (_path, _options, onEvent) => {
            onEvent({ event: 'token', data: { delta: 'Normal answer' } })
            onEvent({ event: 'done', data: {} })
        })

        apiFetchMock.mockResolvedValueOnce({
            id: 3,
            title: 'Normal Chat',
            chat_type: 'normal',
            file_ids: [],
            message_count: 2,
            created_at: '2026-04-15T09:00:00Z',
            updated_at: '2026-04-15T09:10:03Z',
            messages: [
                {
                    id: 301,
                    role: 'user',
                    content: 'Use normal chat',
                    created_at: '2026-04-15T09:10:01Z',
                    updated_at: '2026-04-15T09:10:01Z',
                },
                {
                    id: 302,
                    role: 'assistant',
                    content: 'Normal answer',
                    created_at: '2026-04-15T09:10:02Z',
                    updated_at: '2026-04-15T09:10:02Z',
                },
            ],
        })

        await useChatStore.getState().streamChat(
            { role: 'user', content: 'Use normal chat' },
            'normal',
            { is_web_search_enabled: true }
        )

        const [, options] = apiFetchStreamMock.mock.calls[0]
        expect(JSON.parse(options.body as string)).toMatchObject({
            conversation_id: 3,
            chat_type: 'normal',
            user_question: 'Use normal chat',
            is_web_search_enabled: true,
        })
        expect(apiFetchMock).toHaveBeenCalledWith('/conversations/3')
        expect(useChatStore.getState().messagesByChat[3].map((message) => message.id)).toEqual([301, 302])
    })

    it('reloads server state and rethrows when streaming fails', async () => {
        useChatStore.setState({
            currentChatId: 8,
            activeChatIdByType: {
                normal: 8,
                file: null,
            },
            messagesByChat: { 8: [] },
        })

        apiFetchStreamMock.mockRejectedValueOnce(new Error('stream failed'))
        apiFetchMock.mockResolvedValueOnce({
            id: 8,
            title: 'Recovered Chat',
            chat_type: 'normal',
            file_ids: [],
            message_count: 1,
            created_at: '2026-04-15T10:00:00Z',
            updated_at: '2026-04-15T10:00:03Z',
            messages: [
                {
                    id: 201,
                    role: 'user',
                    content: 'Saved on server',
                    created_at: '2026-04-15T10:00:01Z',
                    updated_at: '2026-04-15T10:00:01Z',
                },
            ],
        })

        await expect(
            useChatStore.getState().streamChat({ role: 'user', content: 'Will fail' })
        ).rejects.toThrow('stream failed')

        expect(apiFetchMock).toHaveBeenCalledWith('/conversations/8')
        expect(useChatStore.getState().messagesByChat[8].map((message) => message.id)).toEqual([201])
        expect(useChatStore.getState().isLoading).toBe(false)
        expect(useChatStore.getState().statusSteps).toEqual([])
    })
})