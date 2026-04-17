import { create } from 'zustand'
import { API_BASE_URL, apiFetch, apiFetchStream, type StreamEvent } from '@/lib/api'
import { useAuthStore } from './auth-store'

export type Skill = {
    id: number
    name: string
    description: string | null
    allowedTools: string | null
    fileType: string
    isActive: boolean
    isSelected: boolean
    size: number
    createdAt: number
}

export type Sandbox = {
    id: number
    sandboxIndex: number
    status: 'ready' | 'busy' | 'error'
    currentSkillId: number | null
    taskDescription: string | null
    progress: number
    startedAt: number | null
    completedAt: number | null
}

export type SkillConversation = {
    id: number
    title: string
    createdAt: number
    updatedAt: number
    messageCount: number
}

export type OutputFile = {
    name: string
    size: number
    sandbox_index: number
    download_url: string
    blob_url?: string | null
}

export type SkillExecutionRun = {
    id: number
    userMessageId: number | null
    assistantMessageId: number | null
    prompt: string
    output: string
    progress: string[]
    liveStatus: string | null
    status: 'running' | 'done' | 'error'
    error: string | null
    attachedFileIds: number[]
    skillIds: number[]
    outputFiles?: OutputFile[]
    createdAt: number
}

type SkillApiResponse = {
    id: number
    name: string
    description: string | null
    allowed_tools: string | null
    file_type: string
    is_active: boolean
    is_selected: boolean
    size: number
    created_at: string
    updated_at: string
}

type SandboxApiResponse = {
    id: number
    sandbox_index: number
    status: string
    current_skill_id: number | null
    task_description: string | null
    progress: number
    started_at: string | null
    completed_at: string | null
}

type ConversationApiResponse = {
    id: number
    title: string
    chat_type: 'skill'
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

export interface SandboxFile {
    name: string
    size: number
    created: number
}

interface AgentSkillsState {
    skills: Skill[]
    sandboxes: Sandbox[]
    conversations: SkillConversation[]
    currentConversationId: number | null
    executionRunsByConversation: Record<number, SkillExecutionRun[]>
    isLoading: boolean
    isUploading: boolean
    isExecuting: boolean
    executionProgress: string[]
    executionOutput: string
    lastExecutionError: string | null
    selectedSkills: number[]
    sandboxFiles: Record<number, SandboxFile[]>

    setCurrentConversation: (conversationId: number | null) => void
    fetchConversations: () => Promise<SkillConversation[]>
    loadConversation: (conversationId: number) => Promise<void>
    createConversation: (title?: string) => Promise<number>
    renameConversation: (conversationId: number, title: string) => Promise<void>
    deleteConversation: (conversationId: number) => Promise<void>
    fetchSkills: () => Promise<void>
    uploadSkill: (file: File) => Promise<Skill>
    updateSkill: (id: number, updates: Partial<Skill>) => Promise<void>
    deleteSkill: (id: number) => Promise<void>
    toggleSkillSelection: (id: number, isSelected: boolean) => Promise<void>
    fetchSandboxes: () => Promise<void>
    executeSkills: (userMessage: string, conversationId: number, skillIds?: number[], attachedFileIds?: number[]) => Promise<void>
    getSelectedSkills: () => Skill[]
    fetchSandboxFiles: (sandboxIndex: number) => Promise<void>
    downloadSandboxFile: (sandboxIndex: number, filename: string) => Promise<void>
}

const mapSkillResponse = (skill: SkillApiResponse): Skill => ({
    id: skill.id,
    name: skill.name,
    description: skill.description,
    allowedTools: skill.allowed_tools,
    fileType: skill.file_type,
    isActive: skill.is_active,
    isSelected: skill.is_selected,
    size: skill.size,
    createdAt: new Date(skill.created_at).getTime(),
})

const mapSandboxResponse = (sandbox: SandboxApiResponse): Sandbox => ({
    id: sandbox.id,
    sandboxIndex: sandbox.sandbox_index,
    status: sandbox.status as 'ready' | 'busy' | 'error',
    currentSkillId: sandbox.current_skill_id,
    taskDescription: sandbox.task_description,
    progress: sandbox.progress,
    startedAt: sandbox.started_at ? new Date(sandbox.started_at).getTime() : null,
    completedAt: sandbox.completed_at ? new Date(sandbox.completed_at).getTime() : null,
})

const mapConversationResponse = (conversation: ConversationApiResponse): SkillConversation => ({
    id: conversation.id,
    title: conversation.title,
    createdAt: new Date(conversation.created_at).getTime(),
    updatedAt: new Date(conversation.updated_at).getTime(),
    messageCount: conversation.message_count,
})

const sortConversations = (conversations: SkillConversation[]) =>
    [...conversations].sort((left, right) => right.updatedAt - left.updatedAt)

const upsertConversation = (
    conversations: SkillConversation[],
    conversation: SkillConversation
): SkillConversation[] => sortConversations([
    conversation,
    ...conversations.filter((item) => item.id !== conversation.id),
])

const deriveRunsFromMessages = (messages: MessageApiResponse[]): SkillExecutionRun[] => {
    const runs: SkillExecutionRun[] = []
    let currentRun: SkillExecutionRun | null = null

    messages.forEach((message) => {
        const createdAt = new Date(message.created_at).getTime()
        if (message.role === 'user') {
            currentRun = {
                id: message.id,
                userMessageId: message.id,
                assistantMessageId: null,
                prompt: message.content,
                output: '',
                progress: [],
                liveStatus: null,
                status: 'done',
                error: null,
                attachedFileIds: [],
                skillIds: [],
                createdAt,
            }
            runs.push(currentRun)
            return
        }

        if (!currentRun) {
            return
        }

        currentRun.assistantMessageId = message.id
        currentRun.output = message.content
        currentRun.status = message.content.startsWith('Execution failed:') ? 'error' : 'done'
        currentRun.error = currentRun.status === 'error'
            ? message.content.replace(/^Execution failed:\s*/i, '')
            : null
    })

    return runs
}

export const useAgentSkillsStore = create<AgentSkillsState>((set, get) => ({
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

    setCurrentConversation: (conversationId) => set({ currentConversationId: conversationId }),

    fetchConversations: async () => {
        const conversations = await apiFetch<ConversationApiResponse[]>('/conversations?chat_type=skill')
        const mappedConversations = sortConversations(conversations.map(mapConversationResponse))

        set((state) => ({
            conversations: mappedConversations,
            currentConversationId:
                state.currentConversationId && mappedConversations.some((conversation) => conversation.id === state.currentConversationId)
                    ? state.currentConversationId
                    : mappedConversations[0]?.id || null,
        }))

        return mappedConversations
    },

    loadConversation: async (conversationId) => {
        const conversation = await apiFetch<ConversationDetailApiResponse>(`/conversations/${conversationId}`)
        const mappedConversation = mapConversationResponse(conversation)
        const derivedRuns = deriveRunsFromMessages(conversation.messages)

        set((state) => ({
            conversations: upsertConversation(state.conversations, mappedConversation),
            currentConversationId: conversationId,
            executionRunsByConversation: {
                ...state.executionRunsByConversation,
                [conversationId]: state.executionRunsByConversation[conversationId]?.length
                    ? state.executionRunsByConversation[conversationId]
                    : derivedRuns,
            },
        }))
    },

    createConversation: async (title) => {
        const response = await apiFetch<ConversationApiResponse>('/conversations', {
            method: 'POST',
            body: JSON.stringify({
                chat_type: 'skill',
                title: title?.trim() || undefined,
                file_ids: [],
            }),
        })

        const conversation = mapConversationResponse(response)
        set((state) => ({
            conversations: upsertConversation(state.conversations, conversation),
            currentConversationId: conversation.id,
            executionRunsByConversation: {
                ...state.executionRunsByConversation,
                [conversation.id]: [],
            },
        }))

        return conversation.id
    },

    renameConversation: async (conversationId, title) => {
        const response = await apiFetch<ConversationApiResponse>(`/conversations/${conversationId}`, {
            method: 'PATCH',
            body: JSON.stringify({ title }),
        })
        const updatedConversation = mapConversationResponse(response)

        set((state) => ({
            conversations: upsertConversation(state.conversations, updatedConversation),
        }))
    },

    deleteConversation: async (conversationId) => {
        await apiFetch(`/conversations/${conversationId}`, { method: 'DELETE' })

        set((state) => {
            const nextRuns = { ...state.executionRunsByConversation }
            delete nextRuns[conversationId]
            const conversations = state.conversations.filter((conversation) => conversation.id !== conversationId)

            return {
                conversations,
                currentConversationId:
                    state.currentConversationId === conversationId
                        ? conversations[0]?.id || null
                        : state.currentConversationId,
                executionRunsByConversation: nextRuns,
            }
        })
    },

    fetchSkills: async () => {
        set({ isLoading: true })
        try {
            const skills = await apiFetch<SkillApiResponse[]>('/skills')
            const mappedSkills = skills.map(mapSkillResponse)
            set({
                skills: mappedSkills,
                selectedSkills: mappedSkills.filter((skill) => skill.isSelected).map((skill) => skill.id),
            })
        } finally {
            set({ isLoading: false })
        }
    },

    uploadSkill: async (file) => {
        set({ isUploading: true })
        try {
            const formData = new FormData()
            formData.append('file', file)

            const response = await apiFetch<SkillApiResponse>('/skills/upload', {
                method: 'POST',
                body: formData,
            })
            const skill = mapSkillResponse(response)

            set((state) => ({
                skills: [skill, ...state.skills],
                selectedSkills: skill.isSelected
                    ? [...state.selectedSkills, skill.id]
                    : state.selectedSkills,
            }))
            return skill
        } finally {
            set({ isUploading: false })
        }
    },

    updateSkill: async (id, updates) => {
        const response = await apiFetch<SkillApiResponse>(`/skills/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(updates),
        })
        const updatedSkill = mapSkillResponse(response)

        set((state) => ({
            skills: state.skills.map((skill) => (skill.id === id ? updatedSkill : skill)),
        }))
    },

    deleteSkill: async (id) => {
        await apiFetch(`/skills/${id}`, { method: 'DELETE' })
        set((state) => ({
            skills: state.skills.filter((skill) => skill.id !== id),
            selectedSkills: state.selectedSkills.filter((skillId) => skillId !== id),
        }))
    },

    toggleSkillSelection: async (id, isSelected) => {
        await apiFetch('/skills/select', {
            method: 'POST',
            body: JSON.stringify({ skill_id: id, is_selected: isSelected }),
        })
        set((state) => ({
            skills: state.skills.map((skill) => (skill.id === id ? { ...skill, isSelected } : skill)),
            selectedSkills: isSelected
                ? [...state.selectedSkills, id]
                : state.selectedSkills.filter((skillId) => skillId !== id),
        }))
    },

    fetchSandboxes: async () => {
        const sandboxes = await apiFetch<SandboxApiResponse[]>('/skills/sandboxes/list')
        set({ sandboxes: sandboxes.map(mapSandboxResponse) })
    },

    executeSkills: async (userMessage, conversationId, skillIds, attachedFileIds = []) => {
        const now = Date.now()
        const selectedSkillIds = skillIds || []
        const runId = now

        set({
            isExecuting: true,
            executionProgress: [],
            executionOutput: '',
            lastExecutionError: null,
        })

        set((state) => ({
            conversations: sortConversations(state.conversations.map((conversation) => {
                if (conversation.id !== conversationId) {
                    return conversation
                }

                return {
                    ...conversation,
                    updatedAt: now,
                }
            })),
            currentConversationId: conversationId,
            executionRunsByConversation: {
                ...state.executionRunsByConversation,
                [conversationId]: [
                    ...(state.executionRunsByConversation[conversationId] || []),
                    {
                        id: runId,
                        userMessageId: null,
                        assistantMessageId: null,
                        prompt: userMessage,
                        output: '',
                        progress: [],
                        liveStatus: null,
                        status: 'running',
                        error: null,
                        attachedFileIds,
                        skillIds: selectedSkillIds,
                        createdAt: now,
                    },
                ],
            },
        }))

        try {
            await apiFetchStream(
                '/skills/execute',
                {
                    method: 'POST',
                    body: JSON.stringify({
                        user_message: userMessage,
                        skill_ids: selectedSkillIds,
                        conversation_id: conversationId,
                    }),
                },
                (evt: StreamEvent) => {
                    if (evt.event === 'status') {
                        const message = evt.data?.message || evt.data?.step
                        if (!message) {
                            return
                        }

                        set((state) => ({
                            executionProgress: [...state.executionProgress, message],
                            executionRunsByConversation: {
                                ...state.executionRunsByConversation,
                                [conversationId]: (state.executionRunsByConversation[conversationId] || []).map((run) =>
                                    run.id === runId
                                        ? { ...run, progress: [...run.progress, message], liveStatus: message }
                                        : run
                                ),
                            },
                        }))
                        return
                    }

                    if (evt.event === 'tool_use') {
                        const message = evt.data?.message as string | undefined
                        if (!message) return
                        set((state) => ({
                            executionRunsByConversation: {
                                ...state.executionRunsByConversation,
                                [conversationId]: (state.executionRunsByConversation[conversationId] || []).map((run) =>
                                    run.id === runId ? { ...run, liveStatus: message } : run
                                ),
                            },
                        }))
                        return
                    }

                    if (evt.event === 'thinking') {
                        const message = evt.data?.message as string | undefined
                        if (!message) return
                        const brief = message.length > 80 ? message.slice(0, 80) + '...' : message
                        set((state) => ({
                            executionRunsByConversation: {
                                ...state.executionRunsByConversation,
                                [conversationId]: (state.executionRunsByConversation[conversationId] || []).map((run) =>
                                    run.id === runId ? { ...run, liveStatus: brief } : run
                                ),
                            },
                        }))
                        return
                    }

                    if (evt.event === 'token') {
                        const delta = evt.data?.delta
                        if (typeof delta !== 'string' || delta.length === 0) {
                            return
                        }

                        set((state) => ({
                            executionOutput: `${state.executionOutput}${delta}`,
                            executionRunsByConversation: {
                                ...state.executionRunsByConversation,
                                [conversationId]: (state.executionRunsByConversation[conversationId] || []).map((run) =>
                                    run.id === runId
                                        ? { ...run, output: `${run.output}${delta}`, status: 'running' }
                                        : run
                                ),
                            },
                        }))
                        return
                    }

                    if (evt.event === 'file') {
                        const file = evt.data as OutputFile
                        if (!file?.name) return

                        set((state) => ({
                            executionRunsByConversation: {
                                ...state.executionRunsByConversation,
                                [conversationId]: (state.executionRunsByConversation[conversationId] || []).map((run) =>
                                    run.id === runId
                                        ? {
                                            ...run,
                                            outputFiles: [...(run.outputFiles || []), file],
                                        }
                                        : run
                                ),
                            },
                        }))
                        return
                    }

                    if (evt.event === 'error') {
                        const message = evt.data?.message || 'Error occurred'
                        set((state) => ({
                            isExecuting: false,
                            lastExecutionError: message,
                            executionProgress: [...state.executionProgress, `Error: ${message}`],
                            executionRunsByConversation: {
                                ...state.executionRunsByConversation,
                                [conversationId]: (state.executionRunsByConversation[conversationId] || []).map((run) =>
                                    run.id === runId
                                        ? { ...run, status: 'error', error: message }
                                        : run
                                ),
                            },
                        }))
                        return
                    }

                    if (evt.event === 'done') {
                        const outputFiles = evt.data?.files as OutputFile[] | undefined
                        set((state) => ({
                            isExecuting: false,
                            executionOutput:
                                typeof evt.data?.output === 'string' && evt.data.output.length > state.executionOutput.length
                                    ? evt.data.output
                                    : state.executionOutput,
                            executionRunsByConversation: {
                                ...state.executionRunsByConversation,
                                [conversationId]: (state.executionRunsByConversation[conversationId] || []).map((run) =>
                                    run.id === runId
                                        ? {
                                            ...run,
                                            output:
                                                typeof evt.data?.output === 'string' && evt.data.output.length > run.output.length
                                                    ? evt.data.output
                                                    : run.output,
                                            status: 'done',
                                            outputFiles: run.outputFiles?.length
                                                    ? run.outputFiles
                                                    : (outputFiles || run.outputFiles),
                                        }
                                        : run
                                ),
                            },
                        }))
                    }
                }
            )

            const conversation = await apiFetch<ConversationDetailApiResponse>(`/conversations/${conversationId}`)
            const mappedConversation = mapConversationResponse(conversation)
            const derivedRuns = deriveRunsFromMessages(conversation.messages)

            set((state) => ({
                conversations: upsertConversation(state.conversations, mappedConversation),
                executionRunsByConversation: {
                    ...state.executionRunsByConversation,
                    [conversationId]: (state.executionRunsByConversation[conversationId] || []).map((run) => {
                        const derivedRun = derivedRuns.find((item) => item.prompt === run.prompt && item.createdAt >= run.createdAt - 1000)
                        return derivedRun
                            ? {
                                ...run,
                                userMessageId: derivedRun.userMessageId,
                                assistantMessageId: derivedRun.assistantMessageId,
                                output: derivedRun.output || run.output,
                                status: derivedRun.status,
                                error: derivedRun.error,
                            }
                            : run
                    }),
                },
            }))
        } finally {
            set({ isExecuting: false })
            void get().fetchSandboxes()
        }
    },

    getSelectedSkills: () => {
        const state = get()
        return state.skills.filter((skill) => skill.isSelected)
    },

    fetchSandboxFiles: async (sandboxIndex: number) => {
        try {
            const response = await apiFetch<{ files: SandboxFile[] }>(`/skills/sandboxes/${sandboxIndex}/files`)
            set((state) => ({
                sandboxFiles: { ...state.sandboxFiles, [sandboxIndex]: response.files },
            }))
        } catch (error) {
            console.error('Failed to fetch sandbox files:', error)
        }
    },

    downloadSandboxFile: async (sandboxIndex: number, filename: string) => {
        try {
            const token = useAuthStore.getState().accessToken
            const response = await fetch(
                `${API_BASE_URL}/skills/sandboxes/${sandboxIndex}/files/${encodeURIComponent(filename)}`,
                {
                    method: 'GET',
                    headers: {
                        Accept: 'application/octet-stream',
                        ...(token ? { Token: token } : {}),
                    },
                }
            )

            if (!response.ok) {
                const errorPayload = await response.json().catch(() => null)
                const message =
                    errorPayload?.message ||
                    errorPayload?.detail ||
                    `Request failed with status ${response.status}`
                throw new Error(message)
            }

            const blob = await response.blob()
            const url = window.URL.createObjectURL(blob)
            const anchor = document.createElement('a')
            anchor.href = url
            anchor.download = filename
            document.body.appendChild(anchor)
            anchor.click()
            document.body.removeChild(anchor)
            window.URL.revokeObjectURL(url)
        } catch (error) {
            console.error('Failed to download file:', error)
            throw error
        }
    },
}))
