import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const {
    toastErrorMock,
    toastSuccessMock,
    fetchRetrievalRecordsMock,
} = vi.hoisted(() => ({
    toastErrorMock: vi.fn(),
    toastSuccessMock: vi.fn(),
    fetchRetrievalRecordsMock: vi.fn(),
}))

vi.mock('sonner', () => ({
    toast: {
        error: toastErrorMock,
        success: toastSuccessMock,
    },
}))

vi.mock('@/lib/retrieval-api', () => ({
    fetchRetrievalRecords: fetchRetrievalRecordsMock,
    parseBBoxJson: vi.fn(() => []),
    groupHighlightsByPage: vi.fn(() => []),
}))

vi.mock('@/components/chat/ChatInterface', () => ({
    ChatInterface: ({ onFileCitationClick }: { onFileCitationClick?: (citation: { citation_label: string; file_id: number; file_name: string; page_no: number | null; chunk_index: number }, messageId: number) => void }) => (
        <div>
            <div>Chat Interface</div>
            <button
                type="button"
                onClick={() => onFileCitationClick?.({
                    citation_label: '2.2',
                    file_id: 2,
                    file_name: 'report_246.pdf',
                    page_no: 2,
                    chunk_index: 0,
                }, 88)}
            >
                Open Citation File 2
            </button>
            <button
                type="button"
                onClick={() => onFileCitationClick?.({
                    citation_label: '1.1',
                    file_id: 1,
                    file_name: 'transformer.pdf',
                    page_no: 4,
                    chunk_index: 0,
                }, 77)}
            >
                Open Citation File 1
            </button>
            <button
                type="button"
                onClick={() => onFileCitationClick?.({
                    citation_label: '2.2',
                    file_id: 0,
                    file_name: '',
                    page_no: null,
                    chunk_index: 0,
                }, 88)}
            >
                Open Stale Citation File 2
            </button>
        </div>
    ),
}))

vi.mock('@/components/pdf/PdfViewer', () => ({
    PdfViewer: ({ url }: { url: string }) => <div>PDF Viewer: {url}</div>,
}))

import ChatWithFilePage from '@/pages/ChatWithFilePage'
import { useChatStore } from '@/store/chat-store'
import { useFileStore, type FileItem } from '@/store/file-store'

const createFile = (overrides: Partial<FileItem>): FileItem => ({
    id: 1,
    name: 'report.pdf',
    type: 'application/pdf',
    size: 1024,
    uploadedAt: Date.parse('2026-04-15T10:00:00Z'),
    sasUrl: null,
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
        refreshSasUrl: vi.fn().mockResolvedValue(null),
        refreshSasUrls: vi.fn().mockResolvedValue(undefined),
        connectIngestionSocket: vi.fn(),
        disconnectIngestionSocket: vi.fn(),
    })
}

const resetChatStore = () => {
    useChatStore.setState({
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
        mode: 'file',
        pendingPlan: null,
        researchPhase: 'idle',
        setCurrentChat: vi.fn(),
        activateChatType: vi.fn(),
        fetchChatSessions: vi.fn().mockResolvedValue([]),
        loadConversation: vi.fn().mockResolvedValue(undefined),
        createNewChat: vi.fn().mockResolvedValue(123),
        addMessage: vi.fn().mockResolvedValue(undefined),
        setConversationOpenScrollBehavior: vi.fn(),
        setInput: vi.fn(),
        setIsLoading: vi.fn(),
        setMode: vi.fn(),
        requestFileChatNew: vi.fn(),
        getCurrentMessages: vi.fn(() => []),
        getChatSessions: vi.fn(() => []),
        deleteChat: vi.fn().mockResolvedValue(undefined),
        renameChat: vi.fn().mockResolvedValue(undefined),
        updateConversationFiles: vi.fn().mockResolvedValue(undefined),
        setPendingPlan: vi.fn(),
        setActiveCitation: vi.fn(),
        getFileChatCitations: vi.fn(() => []),
        streamChat: vi.fn().mockResolvedValue(undefined),
        createDeepResearchPlan: vi.fn(),
        approveDeepResearchPlan: vi.fn(),
    })
}

describe('ChatWithFilePage', () => {
    beforeEach(() => {
        resetFileStore()
        resetChatStore()
        toastErrorMock.mockReset()
        toastSuccessMock.mockReset()
        fetchRetrievalRecordsMock.mockReset()
        fetchRetrievalRecordsMock.mockResolvedValue([])
    })

    it('selects a recent file and enables starting a chat', async () => {
        const user = userEvent.setup()
        useFileStore.setState({
            files: [
                createFile({ id: 1, name: 'Transformer.pdf', size: 2110000, ingestionStatus: 'pending' }),
                createFile({ id: 2, name: 'report_246.pdf', size: 134100, uploadedAt: Date.parse('2026-04-16T10:00:00Z'), ingestionStatus: 'pending' }),
            ],
        })

        render(
            <MemoryRouter initialEntries={['/chat-file']}>
                <ChatWithFilePage />
            </MemoryRouter>
        )

        await waitFor(() => {
            expect(screen.getByRole('button', { name: /start chat with 0 files/i })).toBeDisabled()
        })

        await user.click(screen.getByRole('button', { name: /report_246\.pdf/i }))

        expect(screen.getByText(/selected files \(1\)/i)).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /start chat with 1 file/i })).toBeEnabled()
        expect(screen.getByRole('button', { name: /report_246\.pdf/i })).toHaveAttribute('aria-pressed', 'true')
    })

    it('keeps the file selected after refreshSasUrl updates the file store', async () => {
        const user = userEvent.setup()
        const recentFile = createFile({
            id: 2,
            name: 'report_246.pdf',
            size: 134100,
            uploadedAt: Date.parse('2026-04-16T10:00:00Z'),
            ingestionStatus: 'pending',
        })

        const refreshSasUrlMock = vi.fn().mockImplementation(async (id: number) => {
            useFileStore.setState((state) => ({
                files: state.files.map((file) =>
                    file.id === id ? { ...file, sasUrl: 'https://example.com/file.pdf?sig=test' } : file
                ),
            }))
            return 'https://example.com/file.pdf?sig=test'
        })

        useFileStore.setState({
            files: [
                createFile({ id: 1, name: 'Transformer.pdf', size: 2110000, ingestionStatus: 'pending' }),
                recentFile,
            ],
            refreshSasUrl: refreshSasUrlMock,
        })

        render(
            <MemoryRouter initialEntries={['/chat-file']}>
                <ChatWithFilePage />
            </MemoryRouter>
        )

        await user.click(screen.getByRole('button', { name: /report_246\.pdf/i }))

        await waitFor(() => {
            expect(refreshSasUrlMock).toHaveBeenCalledWith(2)
        })

        expect(screen.getByText(/selected files \(1\)/i)).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /start chat with 1 file/i })).toBeEnabled()
        expect(screen.getByRole('button', { name: /report_246\.pdf/i })).toHaveAttribute('aria-pressed', 'true')
    })

    it('switches to the citation file even when the current preview is not a pdf', async () => {
        const user = userEvent.setup()
        const refreshSasUrlMock = vi.fn().mockImplementation(async (id: number) => `https://example.com/file-${id}`)

        useFileStore.setState({
            files: [
                createFile({ id: 1, name: 'notes.png', type: 'image/png', ingestionStatus: 'completed' }),
                createFile({ id: 2, name: 'report_246.pdf', type: 'application/pdf', ingestionStatus: 'completed' }),
            ],
            refreshSasUrl: refreshSasUrlMock,
        })

        useChatStore.setState({
            currentChatId: 7,
            chatSessions: [
                {
                    id: 7,
                    title: 'Files',
                    createdAt: Date.parse('2026-04-16T10:00:00Z'),
                    updatedAt: Date.parse('2026-04-16T10:00:00Z'),
                    chatType: 'file',
                    fileIds: [1, 2],
                    messageCount: 0,
                },
            ],
            messagesByChat: { 7: [] },
        })

        render(
            <MemoryRouter initialEntries={['/chat-file']}>
                <ChatWithFilePage />
            </MemoryRouter>
        )

        await waitFor(() => {
            expect(refreshSasUrlMock).toHaveBeenCalledWith(1)
        })

        await user.click(screen.getByRole('button', { name: /open citation file 2/i }))

        await waitFor(() => {
            expect(refreshSasUrlMock).toHaveBeenCalledWith(2)
        })

        expect(screen.getByRole('button', { name: /report_246\.pdf/i })).toBeInTheDocument()

        await waitFor(() => {
            expect(screen.getByText('PDF Viewer: https://example.com/file-2')).toBeInTheDocument()
        })
    })

    it('switches from one pdf to another when opening a citation', async () => {
        const user = userEvent.setup()
        const refreshSasUrlMock = vi.fn().mockImplementation(async (id: number) => `https://example.com/file-${id}.pdf`)

        useFileStore.setState({
            files: [
                createFile({ id: 1, name: 'transformer.pdf', type: 'application/pdf', ingestionStatus: 'completed' }),
                createFile({ id: 2, name: 'report_246.pdf', type: 'application/pdf', ingestionStatus: 'completed' }),
            ],
            refreshSasUrl: refreshSasUrlMock,
        })

        useChatStore.setState({
            currentChatId: 8,
            chatSessions: [
                {
                    id: 8,
                    title: 'PDF files',
                    createdAt: Date.parse('2026-04-16T10:00:00Z'),
                    updatedAt: Date.parse('2026-04-16T10:00:00Z'),
                    chatType: 'file',
                    fileIds: [1, 2],
                    messageCount: 0,
                },
            ],
            messagesByChat: { 8: [] },
        })

        render(
            <MemoryRouter initialEntries={['/chat-file']}>
                <ChatWithFilePage />
            </MemoryRouter>
        )

        await waitFor(() => {
            expect(refreshSasUrlMock).toHaveBeenCalledWith(1)
            expect(screen.getByText('PDF Viewer: https://example.com/file-1.pdf')).toBeInTheDocument()
        })

        await user.click(screen.getByRole('button', { name: /open citation file 2/i }))

        await waitFor(() => {
            expect(refreshSasUrlMock).toHaveBeenCalledWith(2)
            expect(screen.getByText('PDF Viewer: https://example.com/file-2.pdf')).toBeInTheDocument()
        })
    })

    it('resolves stale citation metadata from the clicked message before switching files', async () => {
        const user = userEvent.setup()
        const refreshSasUrlMock = vi.fn().mockImplementation(async (id: number) => `https://example.com/file-${id}.pdf`)

        fetchRetrievalRecordsMock.mockImplementation(async (_conversationId: number, messageId: number) => {
            if (messageId === 77) {
                return [
                    {
                        id: 1,
                        chunk_id: 'chunk-1',
                        file_id: 1,
                        file_name: 'transformer.pdf',
                        chunk_index: 0,
                        citation_label: '1.1',
                        page_no: 4,
                        bbox_json: null,
                        chunk_text: null,
                        relevance_score: null,
                    },
                ]
            }

            if (messageId === 88) {
                return [
                    {
                        id: 2,
                        chunk_id: 'chunk-2',
                        file_id: 2,
                        file_name: 'report_246.pdf',
                        chunk_index: 0,
                        citation_label: '2.2',
                        page_no: 2,
                        bbox_json: null,
                        chunk_text: null,
                        relevance_score: null,
                    },
                ]
            }

            return []
        })

        useFileStore.setState({
            files: [
                createFile({ id: 1, name: 'transformer.pdf', type: 'application/pdf', ingestionStatus: 'completed' }),
                createFile({ id: 2, name: 'report_246.pdf', type: 'application/pdf', ingestionStatus: 'completed' }),
            ],
            refreshSasUrl: refreshSasUrlMock,
        })

        useChatStore.setState({
            currentChatId: 81,
            chatSessions: [
                {
                    id: 81,
                    title: 'Citation history',
                    createdAt: Date.parse('2026-04-16T10:00:00Z'),
                    updatedAt: Date.parse('2026-04-16T10:00:00Z'),
                    chatType: 'file',
                    fileIds: [1, 2],
                    messageCount: 0,
                },
            ],
            messagesByChat: { 81: [] },
        })

        render(
            <MemoryRouter initialEntries={['/chat-file']}>
                <ChatWithFilePage />
            </MemoryRouter>
        )

        await waitFor(() => {
            expect(screen.getByText('PDF Viewer: https://example.com/file-1.pdf')).toBeInTheDocument()
        })

        await user.click(screen.getByRole('button', { name: /open citation file 1/i }))

        await waitFor(() => {
            expect(fetchRetrievalRecordsMock).toHaveBeenCalledWith(81, 77)
            expect(screen.getByText(/page 4/i)).toBeInTheDocument()
        })

        await user.click(screen.getByRole('button', { name: /open stale citation file 2/i }))

        await waitFor(() => {
            expect(fetchRetrievalRecordsMock).toHaveBeenCalledWith(81, 88)
            expect(refreshSasUrlMock).toHaveBeenCalledWith(2)
            expect(screen.getByText('PDF Viewer: https://example.com/file-2.pdf')).toBeInTheDocument()
            expect(screen.getByText(/page 2/i)).toBeInTheDocument()
        })
    })

    it('switches preview from the dropdown and clears a stale citation banner', async () => {
        const user = userEvent.setup()
        const refreshSasUrlMock = vi.fn().mockImplementation(async (id: number) => `https://example.com/file-${id}.pdf`)

        useFileStore.setState({
            files: [
                createFile({ id: 1, name: 'transformer.pdf', type: 'application/pdf', ingestionStatus: 'completed' }),
                createFile({ id: 2, name: 'report_246.pdf', type: 'application/pdf', ingestionStatus: 'completed' }),
            ],
            refreshSasUrl: refreshSasUrlMock,
        })

        useChatStore.setState({
            currentChatId: 9,
            chatSessions: [
                {
                    id: 9,
                    title: 'Dropdown files',
                    createdAt: Date.parse('2026-04-16T10:00:00Z'),
                    updatedAt: Date.parse('2026-04-16T10:00:00Z'),
                    chatType: 'file',
                    fileIds: [1, 2],
                    messageCount: 0,
                },
            ],
            messagesByChat: { 9: [] },
        })

        render(
            <MemoryRouter initialEntries={['/chat-file']}>
                <ChatWithFilePage />
            </MemoryRouter>
        )

        await waitFor(() => {
            expect(screen.getByText('PDF Viewer: https://example.com/file-1.pdf')).toBeInTheDocument()
        })

        await user.click(screen.getByRole('button', { name: /open citation file 2/i }))

        await waitFor(() => {
            expect(screen.getByText('PDF Viewer: https://example.com/file-2.pdf')).toBeInTheDocument()
            expect(screen.getByRole('button', { name: /report_246\.pdf/i })).toBeInTheDocument()
            expect(screen.getByText(/page 2/i)).toBeInTheDocument()
        })

        await user.click(screen.getByRole('button', { name: /report_246\.pdf/i }))
        await user.click(await screen.findByRole('button', { name: /transformer\.pdf/i }))

        await waitFor(() => {
            expect(screen.getByText('PDF Viewer: https://example.com/file-1.pdf')).toBeInTheDocument()
        })

        expect(screen.queryByText(/page 2/i)).not.toBeInTheDocument()
        expect(screen.queryByText(/\[2\.2\]/i)).not.toBeInTheDocument()
    })

    it('opens upload flow from add files menu after chat has started', async () => {
        const user = userEvent.setup()

        useFileStore.setState({
            files: [
                createFile({ id: 1, name: 'transformer.pdf', type: 'application/pdf', ingestionStatus: 'completed' }),
            ],
            refreshSasUrl: vi.fn().mockResolvedValue('https://example.com/file-1.pdf'),
        })

        useChatStore.setState({
            currentChatId: 10,
            chatSessions: [
                {
                    id: 10,
                    title: 'Upload files',
                    createdAt: Date.parse('2026-04-16T10:00:00Z'),
                    updatedAt: Date.parse('2026-04-16T10:00:00Z'),
                    chatType: 'file',
                    fileIds: [1],
                    messageCount: 0,
                },
            ],
            messagesByChat: { 10: [] },
        })

        render(
            <MemoryRouter initialEntries={['/chat-file']}>
                <ChatWithFilePage />
            </MemoryRouter>
        )

        await waitFor(() => {
            expect(screen.getByText('PDF Viewer: https://example.com/file-1.pdf')).toBeInTheDocument()
        })

        await user.click(screen.getByRole('button', { name: /add files/i }))
        await user.click(await screen.findByRole('menuitem', { name: /upload files/i }))

        expect(await screen.findByText(/upload files/i)).toBeInTheDocument()
        expect(screen.getByText(/select one or more files from your computer/i)).toBeInTheDocument()
    })
})
