import { create } from 'zustand'
import { io, type Socket } from 'socket.io-client'
import { API_BASE_URL, SOCKET_BASE_URL, apiFetch } from '@/lib/api'
import { useAuthStore } from './auth-store'

export type FileItem = {
    id: number
    name: string
    type: string
    size: number
    uploadedAt: number
    storagePath: string
    ingestionStatus: string
    ingestionError: string | null
    ingestedChunks: number
    ingestedAt: number | null
    ingestionStage?: string
    ingestionProgress?: number
}

type FileApiResponse = {
    id: number
    name: string
    storage_path: string
    mime_type: string
    size: number
    ingestion_status?: string
    ingestion_error?: string | null
    ingested_chunks?: number
    ingested_at?: string | null
    created_at: string
    updated_at: string
}

type IngestionSocketEvent = {
    file_id: number
    status: string
    stage?: string
    progress?: number
    chunks?: number
    error?: string | null
    ingested_at?: string | null
}

interface FileState {
    files: FileItem[]
    isLoading: boolean
    isUploading: boolean
    fetchFiles: () => Promise<void>
    uploadFiles: (files: File[]) => Promise<FileItem[]>
    removeFile: (id: number) => Promise<void>
    renameFile: (id: number, name: string) => Promise<void>
    downloadFile: (id: number) => Promise<void>
    connectIngestionSocket: () => void
    disconnectIngestionSocket: () => void
}

let ingestionSocket: Socket | null = null
let socketToken: string | null = null
let socketSubscriberCount = 0
let socketKeepAliveTimer: ReturnType<typeof setInterval> | null = null
let fetchFilesInFlight: Promise<void> | null = null
let missedSocketHeartbeatCount = 0
const MAX_MISSED_SOCKET_HEARTBEATS = 2

const stopSocketKeepAlive = () => {
    if (socketKeepAliveTimer) {
        clearInterval(socketKeepAliveTimer)
        socketKeepAliveTimer = null
    }
}

const startSocketKeepAlive = () => {
    stopSocketKeepAlive()
    socketKeepAliveTimer = setInterval(() => {
        if (!ingestionSocket || !ingestionSocket.connected) {
            return
        }
        const activeSocket = ingestionSocket
        activeSocket
            .timeout(7000)
            .emit('ingestion_ping', (err: Error | null, response?: { ok?: boolean }) => {
                if (!ingestionSocket || ingestionSocket.id !== activeSocket.id) {
                    return
                }

                if (err || response?.ok !== true) {
                    missedSocketHeartbeatCount += 1
                    if (missedSocketHeartbeatCount >= MAX_MISSED_SOCKET_HEARTBEATS) {
                        missedSocketHeartbeatCount = 0
                        activeSocket.disconnect()
                        activeSocket.connect()
                    }
                    return
                }

                missedSocketHeartbeatCount = 0
            })
    }, 15000)
}

const normalizeIngestionStatus = (
    status?: string,
    stage?: string
): string => {
    const normalizedStatus = (status || '').trim().toLowerCase()
    const normalizedStage = (stage || '').trim().toLowerCase()

    if (normalizedStatus === 'pending' || normalizedStatus === 'completed' || normalizedStatus === 'failed') {
        return normalizedStatus
    }

    if (
        normalizedStatus === 'parsing' ||
        normalizedStatus === 'chunking' ||
        normalizedStatus === 'embedding' ||
        normalizedStatus === 'indexing' ||
        normalizedStatus === 'processing'
    ) {
        return 'processing'
    }

    if (normalizedStage === 'completed' || normalizedStage === 'failed') {
        return normalizedStage
    }

    if (
        normalizedStage === 'parsing' ||
        normalizedStage === 'extracting' ||
        normalizedStage === 'chunking' ||
        normalizedStage === 'embedding' ||
        normalizedStage === 'indexing' ||
        normalizedStage === 'upserting'
    ) {
        return 'processing'
    }

    return 'pending'
}

const toTimestamp = (value?: string | null): number | null => {
    if (!value) {
        return null
    }
    const parsed = new Date(value).getTime()
    return Number.isNaN(parsed) ? null : parsed
}

const mapFileResponse = (file: FileApiResponse): FileItem => {
    const normalizedStatus = normalizeIngestionStatus(file.ingestion_status)
    return {
        id: file.id,
        name: file.name,
        type: file.mime_type,
        size: file.size,
        uploadedAt: new Date(file.created_at).getTime(),
        storagePath: file.storage_path,
        ingestionStatus: normalizedStatus,
        ingestionError: file.ingestion_error ?? null,
        ingestedChunks: file.ingested_chunks ?? 0,
        ingestedAt: toTimestamp(file.ingested_at),
        ingestionStage: normalizedStatus,
        ingestionProgress: normalizedStatus === 'completed' ? 100 : 0,
    }
}

const patchFileIngestionFromSocket = (
    file: FileItem,
    payload: IngestionSocketEvent
): FileItem => {
    const normalizedStatus = normalizeIngestionStatus(payload.status, payload.stage)
    return {
        ...file,
        ingestionStatus: normalizedStatus,
        ingestionError: payload.error ?? null,
        ingestedChunks:
            typeof payload.chunks === 'number' ? payload.chunks : file.ingestedChunks,
        ingestedAt:
            payload.ingested_at === undefined
                ? file.ingestedAt
                : toTimestamp(payload.ingested_at),
        ingestionStage: payload.stage || normalizedStatus || file.ingestionStage,
        ingestionProgress:
            typeof payload.progress === 'number'
                ? Math.max(0, Math.min(100, payload.progress))
                : file.ingestionProgress,
    }
}

export const useFileStore = create<FileState>((set) => ({
    files: [],
    isLoading: false,
    isUploading: false,

    fetchFiles: async () => {
        if (fetchFilesInFlight) {
            return fetchFilesInFlight
        }

        fetchFilesInFlight = (async () => {
            set({ isLoading: true })
            try {
                const files = await apiFetch<FileApiResponse[]>('/files')
                const mappedFiles = files.map(mapFileResponse)
                set({ files: mappedFiles })
            } finally {
                set({ isLoading: false })
                fetchFilesInFlight = null
            }
        })()

        return fetchFilesInFlight
    },

    uploadFiles: async (filesToUpload) => {
        if (filesToUpload.length === 0) {
            return []
        }

        set({ isUploading: true })
        try {
            const formData = new FormData()
            filesToUpload.forEach((file) => formData.append('files', file))

            const response = await apiFetch<FileApiResponse[]>('/files/upload', {
                method: 'POST',
                body: formData,
            })
            const uploadedFiles = response.map(mapFileResponse)

            set((state) => ({
                files: [...uploadedFiles, ...state.files],
            }))
            return uploadedFiles
        } finally {
            set({ isUploading: false })
        }
    },

    removeFile: async (id) => {
        await apiFetch(`/files/${id}`, { method: 'DELETE' })
        set((state) => ({
            files: state.files.filter((f) => f.id !== id),
        }))
    },

    renameFile: async (id, name) => {
        const response = await apiFetch<FileApiResponse>(`/files/${id}`, {
            method: 'PATCH',
            body: JSON.stringify({ name }),
        })
        const renamedFile = mapFileResponse(response)

        set((state) => ({
            files: state.files.map((file) =>
                file.id === id ? renamedFile : file
            ),
        }))
    },

    downloadFile: async (id) => {
        const token = useAuthStore.getState().accessToken
        const response = await fetch(`${API_BASE_URL}/files/${id}/download`, {
            method: 'GET',
            headers: token ? { Token: token } : {},
        })

        if (!response.ok) {
            const errorPayload = await response.json().catch(() => null)
            const message =
                errorPayload?.message ||
                errorPayload?.detail ||
                `Request failed with status ${response.status}`
            throw new Error(message)
        }

        const blob = await response.blob()
        const downloadUrl = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = downloadUrl

        const state = useFileStore.getState()
        const targetFile = state.files.find((file) => file.id === id)
        a.download = targetFile?.name || `file-${id}`

        document.body.appendChild(a)
        a.click()
        a.remove()
        window.URL.revokeObjectURL(downloadUrl)
    },

    connectIngestionSocket: () => {
        const token = useAuthStore.getState().accessToken
        if (!token) {
            return
        }

        socketSubscriberCount += 1
        const requiresReconnect = !ingestionSocket || socketToken !== token
        if (!requiresReconnect) {
            return
        }

        if (ingestionSocket) {
            ingestionSocket.removeAllListeners()
            ingestionSocket.disconnect()
            ingestionSocket = null
        }

        socketToken = token
        ingestionSocket = io(SOCKET_BASE_URL, {
            path: '/socket.io',
            transports: ['polling', 'websocket'],
            query: { token },
            auth: { token },
            reconnection: true,
            reconnectionAttempts: Infinity,
            reconnectionDelay: 1000,
            timeout: 10000,
        })

        ingestionSocket.on('ingestion_status', (payload: IngestionSocketEvent) => {
            if (!payload || typeof payload.file_id !== 'number') {
                return
            }

            const hasFileInStore = useFileStore
                .getState()
                .files.some((file) => file.id === payload.file_id)
            if (!hasFileInStore) {
                void useFileStore.getState().fetchFiles().catch(() => {})
                return
            }

            set((state) => ({
                files: state.files.map((file) =>
                    file.id === payload.file_id
                        ? patchFileIngestionFromSocket(file, payload)
                        : file
                ),
            }))
        })

        ingestionSocket.on('connect', () => {
            missedSocketHeartbeatCount = 0
            startSocketKeepAlive()
            if (useFileStore.getState().files.length === 0) {
                void useFileStore.getState().fetchFiles().catch(() => {})
            }
        })

        ingestionSocket.on('disconnect', () => {
            missedSocketHeartbeatCount = 0
            stopSocketKeepAlive()
        })

        ingestionSocket.on('connect_error', () => {
            missedSocketHeartbeatCount = 0
            stopSocketKeepAlive()
        })
    },

    disconnectIngestionSocket: () => {
        socketSubscriberCount = Math.max(0, socketSubscriberCount - 1)
        if (socketSubscriberCount > 0) {
            return
        }

        if (ingestionSocket) {
            ingestionSocket.removeAllListeners()
            ingestionSocket.disconnect()
            ingestionSocket = null
        }
        socketToken = null
        missedSocketHeartbeatCount = 0
        stopSocketKeepAlive()
    },
}))
