import { create } from 'zustand'
import { API_BASE_URL, apiFetch } from '@/lib/api'
import { useAuthStore } from './auth-store'

export type FileItem = {
    id: number
    name: string
    type: string
    size: number
    uploadedAt: number
    storagePath: string
}

type FileApiResponse = {
    id: number
    name: string
    storage_path: string
    mime_type: string
    size: number
    created_at: string
    updated_at: string
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
}

const mapFileResponse = (file: FileApiResponse): FileItem => ({
    id: file.id,
    name: file.name,
    type: file.mime_type,
    size: file.size,
    uploadedAt: new Date(file.created_at).getTime(),
    storagePath: file.storage_path,
})

export const useFileStore = create<FileState>((set) => ({
    files: [],
    isLoading: false,
    isUploading: false,

    fetchFiles: async () => {
        set({ isLoading: true })
        try {
            const files = await apiFetch<FileApiResponse[]>('/files')
            set({ files: files.map(mapFileResponse) })
        } finally {
            set({ isLoading: false })
        }
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
}))
