import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { navigateMock, toastErrorMock, toastSuccessMock } = vi.hoisted(() => ({
    navigateMock: vi.fn(),
    toastErrorMock: vi.fn(),
    toastSuccessMock: vi.fn(),
}))

vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
    return {
        ...actual,
        useNavigate: () => navigateMock,
    }
})

vi.mock('sonner', () => ({
    toast: {
        error: toastErrorMock,
        success: toastSuccessMock,
    },
}))

import FilesPage from '@/pages/FilesPage'
import { useFileStore, type FileItem } from '@/store/file-store'

const createFile = (overrides: Partial<FileItem>): FileItem => ({
    id: 1,
    name: 'file.txt',
    type: 'text/plain',
    size: 1024,
    uploadedAt: Date.parse('2026-04-15T10:00:00Z'),
    storagePath: 'tmp/file.txt',
    ingestionStatus: 'completed',
    ingestionError: null,
    ingestedChunks: 1,
    ingestedAt: Date.parse('2026-04-15T10:05:00Z'),
    ingestionStage: 'completed',
    ingestionProgress: 100,
    ...overrides,
})

const resetFileStore = () => {
    useFileStore.setState({
        files: [],
        isLoading: false,
        isUploading: false,
        fetchFiles: vi.fn().mockResolvedValue(undefined),
        uploadFiles: vi.fn().mockResolvedValue([]),
        removeFile: vi.fn().mockResolvedValue(undefined),
        renameFile: vi.fn().mockResolvedValue(undefined),
        downloadFile: vi.fn().mockResolvedValue(undefined),
        connectIngestionSocket: vi.fn(),
        disconnectIngestionSocket: vi.fn(),
    })
}

describe('FilesPage', () => {
    beforeEach(() => {
        resetFileStore()
        navigateMock.mockReset()
        toastErrorMock.mockReset()
        toastSuccessMock.mockReset()
    })

    it('renders newest files first by default', () => {
        useFileStore.setState({
            files: [
                createFile({
                    id: 1,
                    name: 'older.pdf',
                    uploadedAt: Date.parse('2026-04-15T09:00:00Z'),
                    type: 'application/pdf',
                }),
                createFile({
                    id: 2,
                    name: 'newer.pdf',
                    uploadedAt: Date.parse('2026-04-15T11:00:00Z'),
                    type: 'application/pdf',
                }),
            ],
        })

        render(
            <MemoryRouter initialEntries={['/files']}>
                <FilesPage />
            </MemoryRouter>
        )

        const olderFile = screen.getByText('older.pdf')
        const newerFile = screen.getByText('newer.pdf')

        expect(
            newerFile.compareDocumentPosition(olderFile) & Node.DOCUMENT_POSITION_FOLLOWING
        ).toBeTruthy()
    })

    it('uploads selected files from the upload dialog', async () => {
        const user = userEvent.setup()
        const uploadFilesMock = vi.fn().mockResolvedValue([])
        useFileStore.setState({ uploadFiles: uploadFilesMock })

        render(
            <MemoryRouter initialEntries={['/files']}>
                <FilesPage />
            </MemoryRouter>
        )

        await user.click(screen.getByRole('button', { name: /upload file/i }))

        const input = document.querySelector('#file-upload-management') as HTMLInputElement
        const file = new File(['hello'], 'notes.txt', { type: 'text/plain' })
        await user.upload(input, file)
        await user.click(screen.getByRole('button', { name: /upload 1 file/i }))

        expect(uploadFilesMock).toHaveBeenCalledWith([file])
        expect(toastSuccessMock).toHaveBeenCalledWith('Uploaded 1 file')
    })
})