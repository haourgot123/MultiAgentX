import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'
import { apiFetch, apiFetchStream, StreamEvent } from '@/lib/api'

export type Message = {
    id: number
    role: 'user' | 'assistant'
    content: string
    timestamp: number
}

export type PlanRequest = {
    sessionId: string
    plan: string[]
    message: string
}

export type ChatSession = {
    id: number
    title: string
    createdAt: number
    updatedAt: number
    chatType: 'normal' | 'file'
    fileIds: number[]
    messageCount: number
}

type ConversationApiResponse = {
    id: number
    title: string
    chat_type: 'normal' | 'file'
    file_ids: number[]
    message_count: number
    created_at: string
    updated_at: string
}

type ConversationDetailApiResponse = ConversationApiResponse & {
    messages: MessageApiResponse[]
}

type MessageApiResponse = {
    id: number
    role: 'user' | 'assistant'
    content: string
    created_at: string
    updated_at: string
}

type AddMessageApiResponse = {
    message: MessageApiResponse
    conversation: ConversationApiResponse
}

type ChatStore = {
    currentChatId: number | null
    chatSessions: ChatSession[]
    messagesByChat: Record<number, Message[]>
    fileChatNewRequestId: number
    input: string
    isLoading: boolean
    statusSteps: string[]
    mode: 'normal' | 'file' | 'deepResearch' | 'webSearch'
    pendingPlan: PlanRequest | null

    setCurrentChat: (id: number | null) => void
    fetchChatSessions: (chatType?: 'normal' | 'file') => Promise<ChatSession[]>
    loadConversation: (id: number) => Promise<void>
    createNewChat: (
        chatType?: 'normal' | 'file',
        options?: { title?: string; fileIds?: number[] }
    ) => Promise<number>
    addMessage: (
        message: Omit<Message, 'id' | 'timestamp'>,
        chatType?: 'normal' | 'file'
    ) => Promise<void>
    setInput: (input: string) => void
    setIsLoading: (loading: boolean) => void
    setMode: (mode: ChatStore['mode']) => void
    requestFileChatNew: () => void
    getCurrentMessages: () => Message[]
    getChatSessions: (chatType?: 'normal' | 'file') => ChatSession[]
    deleteChat: (id: number) => Promise<void>
    renameChat: (id: number, newTitle: string) => Promise<void>
    updateConversationFiles: (id: number, fileIds: number[]) => Promise<void>
    setPendingPlan: (plan: PlanRequest | null) => void
    
    streamChat: (
        message: Omit<Message, 'id' | 'timestamp'>,
        chatType?: 'normal' | 'file',
        options?: {
            is_web_search_enabled?: boolean
            is_deep_research_enabled?: boolean
            is_generate_image_enabled?: boolean
        }
    ) => Promise<void>
    
    createDeepResearchPlan: (
        conversationId: number,
        userQuestion: string
    ) => Promise<PlanRequest>
    
    approveDeepResearchPlan: (
        sessionId: string,
        approvedPlan: string[]
    ) => Promise<void>
}

const mapMessageResponse = (message: MessageApiResponse): Message => ({
    id: message.id,
    role: message.role,
    content: message.content,
    timestamp: new Date(message.created_at).getTime(),
})

const mapConversationResponse = (
    conversation: ConversationApiResponse
): ChatSession => ({
    id: conversation.id,
    title: conversation.title,
    createdAt: new Date(conversation.created_at).getTime(),
    updatedAt: new Date(conversation.updated_at).getTime(),
    chatType: conversation.chat_type,
    fileIds: conversation.file_ids,
    messageCount: conversation.message_count,
})

export const useChatStore = create<ChatStore>()(
    persist(
        (set, get) => ({
            currentChatId: null,
            chatSessions: [],
            messagesByChat: {},
            fileChatNewRequestId: 0,
            input: '',
            isLoading: false,
            statusSteps: [],
            mode: 'normal',
            pendingPlan: null,

    setCurrentChat: (id) => set({ currentChatId: id }),
    
    setPendingPlan: (plan) => set({ pendingPlan: plan }),

    fetchChatSessions: async (chatType) => {
        const queryString = chatType ? `?chat_type=${chatType}` : ''
        const sessions = await apiFetch<ConversationApiResponse[]>(
            `/conversations${queryString}`
        )
        const mappedSessions = sessions.map(mapConversationResponse)

        set((state) => {
            if (!chatType) {
                return { chatSessions: mappedSessions }
            }

            return {
                chatSessions: [
                    ...state.chatSessions.filter((s) => s.chatType !== chatType),
                    ...mappedSessions,
                ].sort((a, b) => b.updatedAt - a.updatedAt),
            }
        })
        return mappedSessions
    },

    loadConversation: async (id) => {
        const conversation = await apiFetch<ConversationDetailApiResponse>(
            `/conversations/${id}`
        )
        const mappedSession = mapConversationResponse(conversation)
        const mappedMessages = conversation.messages.map(mapMessageResponse)

        set((state) => ({
            chatSessions: [
                mappedSession,
                ...state.chatSessions.filter((session) => session.id !== id),
            ].sort((a, b) => b.updatedAt - a.updatedAt),
            messagesByChat: {
                ...state.messagesByChat,
                [id]: mappedMessages,
            },
        }))
    },

    createNewChat: async (chatType = 'normal', options = {}) => {
        const state = get()
        const currentChatId = state.currentChatId
        const currentMessages = currentChatId
            ? state.messagesByChat[currentChatId] || []
            : []

        if (currentChatId && currentMessages.length === 0) {
            try {
                await apiFetch(`/conversations/${currentChatId}`, { method: 'DELETE' })
                set((currentState) => {
                    const remainingMessages = { ...currentState.messagesByChat }
                    delete remainingMessages[currentChatId]
                    return {
                        chatSessions: currentState.chatSessions.filter(
                            (session) => session.id !== currentChatId
                        ),
                        messagesByChat: remainingMessages,
                    }
                })
            } catch {
                // Ignore delete failure for stale empty conversations.
            }
        }

        const payload: {
            chat_type: 'normal' | 'file'
            file_ids: number[]
            title?: string
        } = {
            chat_type: chatType,
            file_ids: options.fileIds || [],
        }

        // File chat must not send custom title; backend will generate default title.
        if (chatType !== 'file' && options.title?.trim()) {
            payload.title = options.title.trim()
        }

        const response = await apiFetch<ConversationApiResponse>('/conversations', {
            method: 'POST',
            body: JSON.stringify(payload),
        })
        const newChat = mapConversationResponse(response)

        set((currentState) => ({
            chatSessions: [
                newChat,
                ...currentState.chatSessions.filter(
                    (session) => session.id !== newChat.id
                ),
            ],
            currentChatId: newChat.id,
            messagesByChat: {
                ...currentState.messagesByChat,
                [newChat.id]: [],
            },
        }))

        return newChat.id
    },

    addMessage: async (message, chatType) => {
        const state = get()
        let currentChatId = state.currentChatId

        if (!currentChatId) {
            currentChatId = await get().createNewChat(chatType)
        }
        if (!currentChatId) {
            return
        }

        const response = await apiFetch<AddMessageApiResponse>(
            `/conversations/${currentChatId}/messages`,
            {
                method: 'POST',
                body: JSON.stringify({
                    role: message.role,
                    content: message.content,
                }),
            }
        )

        const mappedConversation = mapConversationResponse(response.conversation)
        const mappedMessage = mapMessageResponse(response.message)

        set((state) => ({
            // Keep existing title stable for file-chat; title changes should happen via rename endpoint only.
            ...(function () {
                const existingSession = state.chatSessions.find(
                    (session) => session.id === mappedConversation.id
                )
                const stableConversation =
                    mappedConversation.chatType === 'file' && existingSession
                        ? { ...mappedConversation, title: existingSession.title }
                        : mappedConversation

                return {
                    chatSessions: [
                        stableConversation,
                        ...state.chatSessions.filter(
                            (session) => session.id !== stableConversation.id
                        ),
                    ],
                }
            })(),
            messagesByChat: {
                ...state.messagesByChat,
                [currentChatId]: [
                    ...(state.messagesByChat[currentChatId] || []),
                    mappedMessage,
                ],
            },
        }))
    },

    streamChat: async (message, chatType = 'normal', options = {}) => {
        const state = get()
        let currentChatId = state.currentChatId

        if (!currentChatId) {
            currentChatId = await get().createNewChat(chatType)
        }
        if (!currentChatId) {
            return
        }

        // Optimistically add user message
        const optimisticUserMessage: Message = {
            id: Date.now(),
            role: message.role,
            content: message.content,
            timestamp: Date.now(),
        }

        set((state) => ({
            messagesByChat: {
                ...state.messagesByChat,
                [currentChatId as number]: [
                    ...(state.messagesByChat[currentChatId as number] || []),
                    optimisticUserMessage,
                ],
            },
            isLoading: true,
        }))

        // Used to track if the assistant message is created
        let assistantMessageCreated = false;

        try {
            await apiFetchStream(
                '/conversations/chat',
                {
                    method: 'POST',
                    body: JSON.stringify({
                        conversation_id: currentChatId,
                        chat_type: chatType,
                        user_question: message.content,
                        ...options,
                    }),
                },
                (evt: StreamEvent) => {
                    if (evt.event === 'status') {
                        const message = typeof evt.data === 'string' ? evt.data : evt.data?.message
                        if (!message) return

                        set((state) => ({
                            statusSteps: [...state.statusSteps, message],
                            isLoading: true,
                        }))
                        return
                    }

                    if (evt.event === 'token') {
                        const delta: string =
                            typeof evt.data === 'string' ? evt.data : evt.data?.delta || ''
                        if (!delta) return

                        set((state) => {
                            const messages = state.messagesByChat[currentChatId as number] || []
                            const newState: any = {}

                            if (!assistantMessageCreated) {
                                assistantMessageCreated = true
                                newState.statusSteps = []
                                newState.isLoading = false
                                newState.messagesByChat = {
                                    ...state.messagesByChat,
                                    [currentChatId as number]: [
                                        ...messages,
                                        {
                                            id: Date.now() + 1,
                                            role: 'assistant',
                                            content: delta,
                                            timestamp: Date.now() + 1,
                                        },
                                    ],
                                }
                            } else {
                                const lastMessage = messages[messages.length - 1]
                                if (lastMessage && lastMessage.role === 'assistant') {
                                    const updatedMessages = [...messages]
                                    updatedMessages[updatedMessages.length - 1] = {
                                        ...lastMessage,
                                        content: lastMessage.content + delta,
                                    }
                                    newState.messagesByChat = {
                                        ...state.messagesByChat,
                                        [currentChatId as number]: updatedMessages,
                                    }
                                }
                            }

                            return newState
                        })
                        return
                    }

                    if (evt.event === 'done') {
                        set((state) => ({
                            ...state,
                            statusSteps: [],
                            isLoading: false,
                        }))
                        return
                    }

                    if (evt.event === 'error') {
                        const message =
                            typeof evt.data === 'string' ? evt.data : evt.data?.message || 'Error'
                        console.error('Streaming error event:', message)
                        set({ isLoading: false })
                    }
                }
            )
            
            // Reload conversation in the background to sync real IDs from the backend
            get().loadConversation(currentChatId)
            
        } catch (error) {
            console.error('Streaming error:', error)
            // Error handling could be expanded here to update the assistant message to an error state
        } finally {
            set({ isLoading: false })
        }
    },

    setInput: (input) => set({ input }),
    setIsLoading: (isLoading) => set({ isLoading }),
    setMode: (mode) => set({ mode }),
    requestFileChatNew: () =>
        set((state) => ({ fileChatNewRequestId: state.fileChatNewRequestId + 1 })),

    getCurrentMessages: () => {
        const state = get()
        if (!state.currentChatId) {
            return []
        }
        return state.messagesByChat[state.currentChatId] || []
    },

    getChatSessions: (chatType) => {
        const sessions = get().chatSessions
        if (chatType) {
            return sessions.filter((s) => s.chatType === chatType)
        }
        return sessions
    },

    deleteChat: async (id) => {
        await apiFetch(`/conversations/${id}`, { method: 'DELETE' })
        set((state) => {
            const remainingMessages = { ...state.messagesByChat }
            delete remainingMessages[id]
            const newSessions = state.chatSessions.filter((session) => session.id !== id)
            const newCurrentId = state.currentChatId === id
                ? (newSessions[0]?.id || null)
                : state.currentChatId

            return {
                chatSessions: newSessions,
                messagesByChat: remainingMessages,
                currentChatId: newCurrentId,
            }
        })
    },

    renameChat: async (id, newTitle) => {
        const updatedSession = await apiFetch<ConversationApiResponse>(`/conversations/${id}`, {
            method: 'PATCH',
            body: JSON.stringify({ title: newTitle }),
        })
        const mappedSession = mapConversationResponse(updatedSession)

        set((state) => ({
            chatSessions: state.chatSessions.map((session) =>
                session.id === id ? mappedSession : session
            ).sort((a, b) => b.updatedAt - a.updatedAt),
        }))
    },

    createDeepResearchPlan: async (conversationId, userQuestion) => {
        // Don't add status here - backend will emit status events
        useChatStore.setState({ isLoading: true })

        try {
            const response = await apiFetch<{
                session_id: string
                plan: string[]
                message: string
            }>('/conversations/deep-research/plan', {
                method: 'POST',
                body: JSON.stringify({
                    conversation_id: conversationId,
                    user_question: userQuestion,
                }),
            })

            return {
                sessionId: response.session_id,
                plan: response.plan,
                message: response.message,
            }
        } catch (error) {
            useChatStore.setState({ isLoading: false })
            throw error
        }
    },

    approveDeepResearchPlan: async (sessionId, approvedPlan) => {
        const state = get()
        const currentChatId = state.currentChatId

        if (!currentChatId) {
            throw new Error('No active conversation')
        }

        // Add user message about approved plan
        const userMessage: Message = {
            id: Date.now(),
            role: 'user',
            content: `Research plan approved:\n${approvedPlan.map((q, i) => `${i + 1}. ${q}`).join('\n')}`,
            timestamp: Date.now(),
        }

        // Clear status and set loading - backend will emit status events
        useChatStore.setState((state) => ({
            messagesByChat: {
                ...state.messagesByChat,
                [currentChatId]: [
                    ...(state.messagesByChat[currentChatId] || []),
                    userMessage,
                ],
            },
            isLoading: true,
            statusSteps: [],
            pendingPlan: null,
        }))

        let assistantMessageCreated = false

        try {
            await apiFetchStream(
                '/conversations/deep-research/approve',
                {
                    method: 'POST',
                    body: JSON.stringify({
                        session_id: sessionId,
                        approved_plan: approvedPlan,
                    }),
                },
                (evt: StreamEvent) => {
                    if (evt.event === 'status') {
                        const message = typeof evt.data === 'string' ? evt.data : evt.data?.message
                        if (!message) return

                        set((state) => ({
                            statusSteps: [...state.statusSteps, message],
                            isLoading: true,
                        }))
                        return
                    }

                    if (evt.event === 'token') {
                        const delta: string =
                            typeof evt.data === 'string' ? evt.data : evt.data?.delta || ''
                        if (!delta) return

                        set((state) => {
                            const messages = state.messagesByChat[currentChatId] || []
                            const newState: any = {}

                            if (!assistantMessageCreated) {
                                assistantMessageCreated = true
                                newState.statusSteps = []
                                newState.isLoading = false
                                newState.messagesByChat = {
                                    ...state.messagesByChat,
                                    [currentChatId]: [
                                        ...messages,
                                        {
                                            id: Date.now() + 1,
                                            role: 'assistant',
                                            content: delta,
                                            timestamp: Date.now() + 1,
                                        },
                                    ],
                                }
                            } else {
                                const lastMessage = messages[messages.length - 1]
                                if (lastMessage && lastMessage.role === 'assistant') {
                                    const updatedMessages = [...messages]
                                    updatedMessages[updatedMessages.length - 1] = {
                                        ...lastMessage,
                                        content: lastMessage.content + delta,
                                    }
                                    newState.messagesByChat = {
                                        ...state.messagesByChat,
                                        [currentChatId]: updatedMessages,
                                    }
                                }
                            }

                            return newState
                        })
                        return
                    }

                    if (evt.event === 'done') {
                        set((state) => ({
                            ...state,
                            statusSteps: [],
                            isLoading: false,
                        }))
                        return
                    }

                    if (evt.event === 'error') {
                        const message =
                            typeof evt.data === 'string' ? evt.data : evt.data?.message || 'Error'
                        console.error('Streaming error event:', message)
                        set({ isLoading: false })
                    }
                }
            )

            // Note: Don't reload conversation here to avoid overwriting the streamed message
            // The message will be persisted on the backend and will be available on next load
            // get().loadConversation(currentChatId)

        } catch (error) {
            console.error('Deep research streaming error:', error)
        } finally {
            set({ isLoading: false })
        }
    },

            updateConversationFiles: async (id, fileIds) => {
                const updatedSession = await apiFetch<ConversationApiResponse>(
                    `/conversations/${id}/files`,
                    {
                        method: 'PUT',
                        body: JSON.stringify({ file_ids: fileIds }),
                    }
                )
                const mappedSession = mapConversationResponse(updatedSession)

                set((state) => ({
                    ...(function () {
                        const existingSession = state.chatSessions.find(
                            (session) => session.id === id
                        )
                        const stableSession =
                            mappedSession.chatType === 'file' && existingSession
                                ? { ...mappedSession, title: existingSession.title }
                                : mappedSession

                        return {
                            chatSessions: state.chatSessions
                                .map((session) =>
                                    session.id === id ? stableSession : session
                                )
                                .sort((a, b) => b.updatedAt - a.updatedAt),
                        }
                    })(),
                }))
            },
        }),
        {
            name: 'chat-storage',
            storage: createJSONStorage(() => sessionStorage),
            partialize: (state) => ({
                currentChatId: state.currentChatId,
                mode: state.mode,
            }),
        }
    )
)
