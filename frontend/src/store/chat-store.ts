import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'
import { apiFetch, apiFetchStream, type StreamEvent } from '@/lib/api'

export type Message = {
    id: number
    role: 'user' | 'assistant'
    content: string
    timestamp: number
}

export type FileCitation = {
    citation_label: string
    file_id: number
    file_name: string
    page_no: number | null
    chunk_index: number
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
    activeChatIdByType: Record<'normal' | 'file', number | null>
    chatSessions: ChatSession[]
    messagesByChat: Record<number, Message[]>
    fileChatNewRequestId: number
    fileChatCitations: Record<number, FileCitation[]>  // keyed by conversation_id
    activeCitation: FileCitation | null
    input: string
    isLoading: boolean
    loadingChatId: number | null
    conversationOpenScrollBehavior: 'auto' | 'smooth' | null
    statusSteps: string[]
    mode: 'normal' | 'file' | 'deepResearch' | 'webSearch'
    pendingPlan: PlanRequest | null
    researchPhase: 'idle' | 'planning' | 'researching'

    setCurrentChat: (id: number | null, chatType?: 'normal' | 'file') => void
    activateChatType: (chatType: 'normal' | 'file') => void
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
    setConversationOpenScrollBehavior: (behavior: 'auto' | 'smooth' | null) => void
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
    setActiveCitation: (citation: FileCitation | null) => void
    getFileChatCitations: () => FileCitation[]
    
    streamChat: (
        message: Omit<Message, 'id' | 'timestamp'>,
        chatType?: 'normal' | 'file',
        options?: {
            is_web_search_enabled?: boolean
            is_deep_research_enabled?: boolean
            is_generate_image_enabled?: boolean
            route_preference?: 'auto' | 'websearch_agent' | 'deep_research_agent' | 'image_generation_agent'
            file_ids?: number[]
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

const sortMessages = (messages: Message[]): Message[] =>
    [...messages].sort((left, right) => {
        if (left.timestamp !== right.timestamp) {
            return left.timestamp - right.timestamp
        }

        return left.id - right.id
    })

const ensureSortedMessages = (messages: Message[]): Message[] => {
    for (let index = 1; index < messages.length; index += 1) {
        const previous = messages[index - 1]
        const current = messages[index]

        if (
            previous.timestamp > current.timestamp ||
            (previous.timestamp === current.timestamp && previous.id > current.id)
        ) {
            return sortMessages(messages)
        }
    }

    return messages
}

const appendMessage = (messages: Message[], message: Message): Message[] =>
    sortMessages([...messages, message])

const mergeAssistantDelta = (
    state: Pick<ChatStore, 'messagesByChat' | 'statusSteps' | 'isLoading' | 'loadingChatId'>,
    chatId: number,
    delta: string
) => {
    const messages = state.messagesByChat[chatId] || []
    const lastMessage = messages[messages.length - 1]

    if (lastMessage && lastMessage.role === 'assistant') {
        const updatedMessages = [...messages]
        updatedMessages[updatedMessages.length - 1] = {
            ...lastMessage,
            content: lastMessage.content + delta,
        }

        return {
            statusSteps: [],
            isLoading: false,
            loadingChatId: chatId,
            messagesByChat: {
                ...state.messagesByChat,
                [chatId]: updatedMessages,
            },
        }
    }

    return {
        statusSteps: [],
        isLoading: false,
        loadingChatId: chatId,
        messagesByChat: {
            ...state.messagesByChat,
            [chatId]: appendMessage(messages, {
                id: Date.now() + 1,
                role: 'assistant' as const,
                content: delta,
                timestamp: Date.now() + 1,
            }),
        },
    }
}

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

const getFallbackChatIdForType = (
    state: Pick<ChatStore, 'activeChatIdByType' | 'chatSessions'>,
    chatType: 'normal' | 'file'
): number | null => {
    const preferredChatId = state.activeChatIdByType[chatType]
    if (preferredChatId) {
        return preferredChatId
    }

    return state.chatSessions.find((session) => session.chatType === chatType)?.id || null
}

const resolveActiveChatId = (
    state: Pick<ChatStore, 'activeChatIdByType' | 'chatSessions' | 'currentChatId' | 'mode'>,
    chatType: 'normal' | 'file'
): number | null => {
    const currentSession = state.chatSessions.find(
        (session) => session.id === state.currentChatId
    )

    if (currentSession?.chatType === chatType) {
        return currentSession.id
    }

    return getFallbackChatIdForType(state, chatType)
}

const resolveChatTypeForSelection = (
    state: Pick<ChatStore, 'chatSessions' | 'mode'>,
    id: number | null,
    explicitChatType?: 'normal' | 'file'
): 'normal' | 'file' | null => {
    if (explicitChatType) {
        return explicitChatType
    }

    if (id === null) {
        return state.mode === 'file' ? 'file' : 'normal'
    }

    return state.chatSessions.find((session) => session.id === id)?.chatType || null
}

export const useChatStore = create<ChatStore>()(
    persist(
        (set, get) => ({
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
            loadingChatId: null,
            conversationOpenScrollBehavior: null,
            statusSteps: [],
            mode: 'normal',
            pendingPlan: null,
            researchPhase: 'idle',

    setCurrentChat: (id, chatType) => set((state) => {
        const resolvedChatType = resolveChatTypeForSelection(state, id, chatType)

        if (!resolvedChatType) {
            return { currentChatId: id }
        }

        return {
            currentChatId: id,
            activeChatIdByType: {
                ...state.activeChatIdByType,
                [resolvedChatType]: id,
            },
        }
    }),

    activateChatType: (chatType) => set((state) => ({
        mode: chatType,
        currentChatId: getFallbackChatIdForType(state, chatType),
    })),
    
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
        const mappedMessages = sortMessages(
            conversation.messages.map(mapMessageResponse)
        )

        set((state) => ({
            chatSessions: [
                mappedSession,
                ...state.chatSessions.filter((session) => session.id !== id),
            ].sort((a, b) => b.updatedAt - a.updatedAt),
            activeChatIdByType: {
                ...state.activeChatIdByType,
                [mappedSession.chatType]: id,
            },
            messagesByChat: {
                ...state.messagesByChat,
                [id]: mappedMessages,
            },
        }))
    },

    createNewChat: async (chatType = 'normal', options = {}) => {
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
            activeChatIdByType: {
                ...currentState.activeChatIdByType,
                [newChat.chatType]: newChat.id,
            },
            messagesByChat: {
                ...currentState.messagesByChat,
                [newChat.id]: [],
            },
        }))

        return newChat.id
    },

    addMessage: async (message, chatType) => {
        const state = get()
        const targetChatType = chatType || 'normal'
        let currentChatId = resolveActiveChatId(state, targetChatType)

        if (!currentChatId) {
            currentChatId = await get().createNewChat(targetChatType)
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
                [currentChatId]: appendMessage(
                    state.messagesByChat[currentChatId] || [],
                    mappedMessage
                ),
            },
        }))
    },

    streamChat: async (message, chatType = 'normal', options = {}) => {
        const state = get()
        let currentChatId = resolveActiveChatId(state, chatType)

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
                [currentChatId as number]: appendMessage(
                    state.messagesByChat[currentChatId as number] || [],
                    optimisticUserMessage
                ),
            },
            isLoading: true,
            loadingChatId: currentChatId,
            statusSteps: [],
        }))

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
                            loadingChatId: currentChatId,
                        }))
                        return
                    }

                    if (evt.event === 'token') {
                        const delta: string =
                            typeof evt.data === 'string' ? evt.data : evt.data?.delta || ''
                        if (!delta) return

                        set((state) => mergeAssistantDelta(state, currentChatId as number, delta))
                        return
                    }

                    if (evt.event === 'done') {
                        // Store citations from file chat
                        const citations = evt.data?.citations as FileCitation[] | undefined
                        set((state) => ({
                            ...state,
                            statusSteps: [],
                            isLoading: false,
                            loadingChatId: null,
                            ...(citations && citations.length > 0 && currentChatId ? {
                                fileChatCitations: {
                                    ...state.fileChatCitations,
                                    [currentChatId]: citations,
                                },
                            } : {}),
                        }))
                        return
                    }

                    if (evt.event === 'error') {
                        const message =
                            typeof evt.data === 'string' ? evt.data : evt.data?.message || 'Error'
                        console.error('Streaming error event:', message)
                        set({ isLoading: false, loadingChatId: null })
                    }
                }
            )
            
            await get().loadConversation(currentChatId)
            
        } catch (error) {
            console.error('Streaming error:', error)
            if (currentChatId) {
                try {
                    await get().loadConversation(currentChatId)
                } catch (reloadError) {
                    console.error('Failed to reload conversation after streaming error:', reloadError)
                }
            }
            throw error
        } finally {
            set({ isLoading: false, loadingChatId: null, statusSteps: [] })
        }
    },

    setConversationOpenScrollBehavior: (conversationOpenScrollBehavior) =>
        set({ conversationOpenScrollBehavior }),
    setInput: (input) => set({ input }),
    setIsLoading: (isLoading) => set({ isLoading }),
    setMode: (mode) => set({ mode }),
    setActiveCitation: (citation) => set({ activeCitation: citation }),
    getFileChatCitations: () => {
        const state = get()
        if (!state.currentChatId) return []
        return state.fileChatCitations[state.currentChatId] || []
    },
    requestFileChatNew: () =>
        set((state) => ({ fileChatNewRequestId: state.fileChatNewRequestId + 1 })),

    getCurrentMessages: () => {
        const state = get()
        if (!state.currentChatId) {
            return []
        }
        return ensureSortedMessages(state.messagesByChat[state.currentChatId] || [])
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
            const deletedSession = state.chatSessions.find((session) => session.id === id)
            const deletedChatType = deletedSession?.chatType || null
            const nextActiveByType = deletedChatType
                ? {
                    ...state.activeChatIdByType,
                    [deletedChatType]:
                        newSessions.find((session) => session.chatType === deletedChatType)?.id || null,
                }
                : state.activeChatIdByType

            const newCurrentId = state.currentChatId === id && deletedChatType
                ? getFallbackChatIdForType(
                    {
                        activeChatIdByType: nextActiveByType,
                        chatSessions: newSessions,
                    },
                    deletedChatType
                )
                : state.currentChatId

            return {
                chatSessions: newSessions,
                messagesByChat: remainingMessages,
                activeChatIdByType: nextActiveByType,
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
        useChatStore.setState({
            isLoading: true,
            loadingChatId: conversationId,
            researchPhase: 'planning',
        })

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
            useChatStore.setState({
                isLoading: false,
                loadingChatId: null,
                researchPhase: 'idle',
            })
            throw error
        }
    },

    approveDeepResearchPlan: async (sessionId, approvedPlan) => {
        const state = get()
        const currentChatId = state.currentChatId

        if (!currentChatId) {
            throw new Error('No active conversation')
        }

        const approvedPlanMessage = `Research Plan Approved:\n${approvedPlan
            .map((question, index) => `${index + 1}. ${question}`)
            .join('\n')}`

        const optimisticPlanMessage: Message = {
            id: Date.now(),
            role: 'user',
            content: approvedPlanMessage,
            timestamp: Date.now(),
        }

        set((currentState) => ({
            isLoading: true,
            loadingChatId: currentChatId,
            statusSteps: [],
            pendingPlan: null,
            researchPhase: 'researching',
            messagesByChat: {
                ...currentState.messagesByChat,
                [currentChatId]: appendMessage(
                    currentState.messagesByChat[currentChatId] || [],
                    optimisticPlanMessage
                ),
            },
        }))

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
                            loadingChatId: currentChatId,
                        }))
                        return
                    }

                    if (evt.event === 'token') {
                        const delta: string =
                            typeof evt.data === 'string' ? evt.data : evt.data?.delta || ''
                        if (!delta) return

                        set((state) => mergeAssistantDelta(state, currentChatId, delta))
                        return
                    }

                    if (evt.event === 'done') {
                        set((state) => ({
                            ...state,
                            statusSteps: [],
                            isLoading: false,
                            loadingChatId: null,
                            researchPhase: 'idle',
                        }))
                        return
                    }

                    if (evt.event === 'error') {
                        const message =
                            typeof evt.data === 'string' ? evt.data : evt.data?.message || 'Error'
                        console.error('Deep research streaming error event:', message)
                        set({ isLoading: false, loadingChatId: null, researchPhase: 'idle' })
                    }
                }
            )

            await get().loadConversation(currentChatId)

        } catch (error) {
            console.error('Deep research streaming error:', error)
            try {
                await get().loadConversation(currentChatId)
            } catch (reloadError) {
                console.error('Failed to reload conversation after deep research error:', reloadError)
            }
            throw error
        } finally {
            set({ isLoading: false, loadingChatId: null, researchPhase: 'idle' })
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
                activeChatIdByType: state.activeChatIdByType,
                mode: state.mode,
            }),
        }
    )
)
