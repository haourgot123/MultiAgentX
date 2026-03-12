import { create } from 'zustand'
import { apiFetch } from '@/lib/api'

export type Message = {
    id: number
    role: 'user' | 'assistant'
    content: string
    timestamp: number
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
    input: string
    isLoading: boolean
    mode: 'normal' | 'file' | 'deepResearch' | 'webSearch'

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
    getCurrentMessages: () => Message[]
    getChatSessions: (chatType?: 'normal' | 'file') => ChatSession[]
    deleteChat: (id: number) => Promise<void>
    renameChat: (id: number, newTitle: string) => Promise<void>
    updateConversationFiles: (id: number, fileIds: number[]) => Promise<void>
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

export const useChatStore = create<ChatStore>((set, get) => ({
    currentChatId: null,
    chatSessions: [],
    messagesByChat: {},
    input: '',
    isLoading: false,
    mode: 'normal',

    setCurrentChat: (id) => set({ currentChatId: id }),

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

        const response = await apiFetch<ConversationApiResponse>('/conversations', {
            method: 'POST',
            body: JSON.stringify({
                chat_type: chatType,
                title: options.title,
                file_ids: options.fileIds || [],
            }),
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
            chatSessions: [
                mappedConversation,
                ...state.chatSessions.filter(
                    (session) => session.id !== mappedConversation.id
                ),
            ],
            messagesByChat: {
                ...state.messagesByChat,
                [currentChatId]: [
                    ...(state.messagesByChat[currentChatId] || []),
                    mappedMessage,
                ],
            },
        }))
    },

    setInput: (input) => set({ input }),
    setIsLoading: (isLoading) => set({ isLoading }),
    setMode: (mode) => set({ mode }),

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
            chatSessions: state.chatSessions.map((session) =>
                session.id === id ? mappedSession : session
            ).sort((a, b) => b.updatedAt - a.updatedAt),
        }))
    },
}))
