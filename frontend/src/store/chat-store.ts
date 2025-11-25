import { create } from 'zustand'

export type Message = {
    id: string
    role: 'user' | 'assistant'
    content: string
    timestamp: number
}

export type ChatSession = {
    id: string
    title: string
    messages: Message[]
    createdAt: number
    updatedAt: number
    chatType: 'normal' | 'file'  // Track which type of chat this is
}

type ChatStore = {
    currentChatId: string | null
    chatSessions: ChatSession[]
    input: string
    isLoading: boolean
    mode: 'normal' | 'file' | 'deepResearch' | 'webSearch'

    // Actions
    setCurrentChat: (id: string) => void
    createNewChat: (chatType?: 'normal' | 'file') => string
    addMessage: (message: Omit<Message, 'id' | 'timestamp'>, chatType?: 'normal' | 'file') => void
    setInput: (input: string) => void
    setIsLoading: (loading: boolean) => void
    setMode: (mode: ChatStore['mode']) => void
    getCurrentMessages: () => Message[]
    getChatSessions: (chatType?: 'normal' | 'file') => ChatSession[]
    deleteChat: (id: string) => void
    renameChat: (id: string, newTitle: string) => void
}

export const useChatStore = create<ChatStore>((set, get) => ({
    currentChatId: null,
    chatSessions: [],
    input: '',
    isLoading: false,
    mode: 'normal',

    setCurrentChat: (id) => set({ currentChatId: id }),

    createNewChat: (chatType = 'normal') => {
        const state = get()
        const currentChatId = state.currentChatId
        let sessions = state.chatSessions

        // If current chat is empty, remove it
        if (currentChatId) {
            const currentSession = sessions.find(s => s.id === currentChatId)
            if (currentSession && currentSession.messages.length === 0) {
                sessions = sessions.filter(s => s.id !== currentChatId)
            }
        }

        const newId = `chat-${Date.now()}`
        const newChat: ChatSession = {
            id: newId,
            title: 'New Chat',
            messages: [],
            createdAt: Date.now(),
            updatedAt: Date.now(),
            chatType,
        }
        set({
            chatSessions: [newChat, ...sessions],
            currentChatId: newId,
        })
        return newId
    },

    addMessage: (message, chatType) => {
        const state = get()
        let currentChatId = state.currentChatId

        // If no current chat, create one with the specified type
        if (!currentChatId) {
            currentChatId = get().createNewChat(chatType)
        }

        const newMessage: Message = {
            ...message,
            id: `msg-${Date.now()}`,
            timestamp: Date.now(),
        }

        set((state) => ({
            chatSessions: state.chatSessions.map((session) =>
                session.id === currentChatId
                    ? {
                        ...session,
                        messages: [...session.messages, newMessage],
                        updatedAt: Date.now(),
                        // Update title based on first user message
                        title:
                            session.messages.length === 0 && message.role === 'user'
                                ? message.content.slice(0, 50) + (message.content.length > 50 ? '...' : '')
                                : session.title,
                    }
                    : session
            ),
        }))
    },

    setInput: (input) => set({ input }),
    setIsLoading: (isLoading) => set({ isLoading }),
    setMode: (mode) => set({ mode }),

    getCurrentMessages: () => {
        const state = get()
        const currentSession = state.chatSessions.find((s) => s.id === state.currentChatId)
        return currentSession?.messages || []
    },

    getChatSessions: (chatType) => {
        const sessions = get().chatSessions
        if (chatType) {
            return sessions.filter(s => s.chatType === chatType)
        }
        return sessions
    },

    deleteChat: (id) => {
        set((state) => {
            const newSessions = state.chatSessions.filter((s) => s.id !== id)
            const newCurrentId = state.currentChatId === id
                ? (newSessions[0]?.id || null)
                : state.currentChatId

            return {
                chatSessions: newSessions,
                currentChatId: newCurrentId,
            }
        })
    },

    renameChat: (id, newTitle) => {
        set((state) => ({
            chatSessions: state.chatSessions.map((session) =>
                session.id === id
                    ? { ...session, title: newTitle, updatedAt: Date.now() }
                    : session
            ),
        }))
    },
}))
