import { create } from 'zustand'

export type FileItem = {
    id: string
    name: string
    type: string
    size: number
    uploadedAt: number
}

interface FileState {
    files: FileItem[]
    addFile: (file: Omit<FileItem, 'id' | 'uploadedAt'>) => void
    removeFile: (id: string) => void
}

export const useFileStore = create<FileState>((set) => ({
    files: [
        {
            id: '1',
            name: 'Project_Specs.pdf',
            type: 'application/pdf',
            size: 1024 * 1024 * 2.5, // 2.5MB
            uploadedAt: Date.now() - 100000,
        },
        {
            id: '2',
            name: 'data_analysis.csv',
            type: 'text/csv',
            size: 1024 * 500, // 500KB
            uploadedAt: Date.now() - 200000,
        }
    ],
    addFile: (file) => set((state) => ({
        files: [
            ...state.files,
            {
                ...file,
                id: Math.random().toString(36).substring(7),
                uploadedAt: Date.now(),
            },
        ],
    })),
    removeFile: (id) => set((state) => ({
        files: state.files.filter((f) => f.id !== id),
    })),
}))
