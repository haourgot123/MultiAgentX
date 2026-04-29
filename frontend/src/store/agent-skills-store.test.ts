import { beforeEach, describe, expect, it, vi } from 'vitest'

const { apiFetchMock, apiFetchStreamMock, socketMock } = vi.hoisted(() => ({
    apiFetchMock: vi.fn(),
    apiFetchStreamMock: vi.fn(),
    socketMock: {
        on: vi.fn(),
        removeAllListeners: vi.fn(),
        disconnect: vi.fn(),
    },
}))

vi.mock('@/lib/api', () => ({
    API_BASE_URL: 'http://localhost:8000/api',
    SOCKET_BASE_URL: 'http://localhost:8000',
    apiFetch: apiFetchMock,
    apiFetchStream: apiFetchStreamMock,
}))

vi.mock('socket.io-client', () => ({
    io: vi.fn(() => socketMock),
}))

import { useAgentSkillsStore } from '@/store/agent-skills-store'

const resetStore = () => {
    useAgentSkillsStore.setState({
        skills: [],
        sandboxes: [],
        conversations: [],
        currentConversationId: null,
        executionRunsByConversation: {},
        isLoading: false,
        isUploading: false,
        isExecuting: false,
        executionProgress: [],
        executionOutput: '',
        lastExecutionError: null,
        selectedSkills: [],
        sandboxFiles: {},
    })
}

describe('useAgentSkillsStore', () => {
    beforeEach(() => {
        apiFetchMock.mockReset()
        apiFetchStreamMock.mockReset()
        socketMock.on.mockReset()
        socketMock.removeAllListeners.mockReset()
        socketMock.disconnect.mockReset()
        resetStore()
    })

    it('derives generated output files from assistant message blob metadata', async () => {
        apiFetchMock.mockResolvedValueOnce({
            id: 9,
            title: 'Skill Chat',
            chat_type: 'skill',
            file_ids: [],
            message_count: 2,
            created_at: '2026-04-15T10:00:00Z',
            updated_at: '2026-04-15T10:00:03Z',
            messages: [
                {
                    id: 91,
                    role: 'user',
                    content: 'Create a product presentation',
                    created_at: '2026-04-15T10:00:01Z',
                    updated_at: '2026-04-15T10:00:01Z',
                },
                {
                    id: 92,
                    role: 'assistant',
                    content: 'Created the presentation.',
                    blob_path: 'skill-outputs/1/9/product-presentation.pptx',
                    blob_name: 'product-presentation.pptx',
                    blob_content_type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                    blob_size: 8192,
                    blob_url: 'https://blob.example.com/product-presentation.pptx?sig=test',
                    created_at: '2026-04-15T10:00:02Z',
                    updated_at: '2026-04-15T10:00:02Z',
                },
            ],
        })

        await useAgentSkillsStore.getState().loadConversation(9)

        const runs = useAgentSkillsStore.getState().executionRunsByConversation[9]
        expect(runs).toHaveLength(1)
        expect(runs[0]).toMatchObject({
            userMessageId: 91,
            assistantMessageId: 92,
            prompt: 'Create a product presentation',
            output: 'Created the presentation.',
            status: 'done',
        })
        expect(runs[0].outputFiles).toEqual([
            {
                name: 'product-presentation.pptx',
                size: 8192,
                sandbox_index: -1,
                download_url: 'https://blob.example.com/product-presentation.pptx?sig=test',
                blob_url: 'https://blob.example.com/product-presentation.pptx?sig=test',
                blob_path: 'skill-outputs/1/9/product-presentation.pptx',
                content_type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            },
        ])
    })

    it('merges persisted assistant blob files after skill execution reloads the conversation', async () => {
        const now = new Date().toISOString()
        useAgentSkillsStore.setState({
            conversations: [{
                id: 10,
                title: 'Skill Chat',
                createdAt: Date.parse(now),
                updatedAt: Date.parse(now),
                messageCount: 0,
            }],
            currentConversationId: 10,
            executionRunsByConversation: { 10: [] },
        })
        apiFetchStreamMock.mockImplementationOnce(async (_path, _options, onEvent) => {
            onEvent({
                event: 'done',
                data: {
                    output: 'Created the presentation.',
                    files: [],
                },
            })
        })
        apiFetchMock
            .mockResolvedValueOnce({
                id: 10,
                title: 'Skill Chat',
                chat_type: 'skill',
                file_ids: [],
                message_count: 2,
                created_at: now,
                updated_at: now,
                messages: [
                    {
                        id: 101,
                        role: 'user',
                        content: 'Create a product presentation',
                        created_at: now,
                        updated_at: now,
                    },
                    {
                        id: 102,
                        role: 'assistant',
                        content: 'Created the presentation.',
                        blob_path: 'skill-outputs/1/10/product-presentation.pptx',
                        blob_name: 'product-presentation.pptx',
                        blob_content_type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                        blob_size: 8192,
                        blob_url: 'https://blob.example.com/product-presentation.pptx?sig=test',
                        created_at: now,
                        updated_at: now,
                    },
                ],
            })
            .mockResolvedValueOnce([])

        await useAgentSkillsStore.getState().executeSkills(
            'Create a product presentation',
            10,
            [7]
        )

        const runs = useAgentSkillsStore.getState().executionRunsByConversation[10]
        expect(apiFetchStreamMock).toHaveBeenCalledWith(
            '/skills/execute',
            {
                method: 'POST',
                body: JSON.stringify({
                    user_message: 'Create a product presentation',
                    skill_ids: [7],
                    conversation_id: 10,
                }),
            },
            expect.any(Function)
        )
        expect(runs[0]).toMatchObject({
            userMessageId: 101,
            assistantMessageId: 102,
            output: 'Created the presentation.',
            status: 'done',
        })
        expect(runs[0].outputFiles?.[0]).toMatchObject({
            name: 'product-presentation.pptx',
            blob_path: 'skill-outputs/1/10/product-presentation.pptx',
            blob_url: 'https://blob.example.com/product-presentation.pptx?sig=test',
        })
    })
})
