import { ChatInterface } from "@/components/chat/ChatInterface"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { FileText, Download, Trash2, RefreshCw, ChevronDown, FolderOpen, Upload, X, ChevronUp, ScanSearch, Check } from "lucide-react"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
    DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { fetchRetrievalRecords, parseBBoxJson, groupHighlightsByPage, type RetrievalRecordResponse } from "@/lib/retrieval-api"
import { type FileItem, useFileStore } from "@/store/file-store"
import { lazy, Suspense, useState, useEffect, useRef, useCallback, useMemo } from "react"
import { useSearchParams } from "react-router-dom"
import { useChatStore, type FileCitation } from "@/store/chat-store"
import { toast } from "sonner"

const PdfViewer = lazy(() => import("@/components/pdf/PdfViewer").then((module) => ({ default: module.PdfViewer })))

export default function ChatWithFilePage() {
    const [searchParams] = useSearchParams()
    const fileIdFromUrl = searchParams.get('fileId')
    const { files, fetchFiles, uploadFiles, isUploading, downloadFile, refreshSasUrl } = useFileStore()
    const {
        createNewChat,
        currentChatId,
        chatSessions,
        messagesByChat,
        loadConversation,
        updateConversationFiles,
        fileChatNewRequestId,
    } = useChatStore()

    const [selectedFile, setSelectedFile] = useState<FileItem | null>(null)
    const [showUploadDialog, setShowUploadDialog] = useState(false)
    const [showLibraryDialog, setShowLibraryDialog] = useState(false)
    const [availableFiles, setAvailableFiles] = useState<FileItem[]>([])
    const [pendingLibraryFiles, setPendingLibraryFiles] = useState<FileItem[]>([])
    const [hasStartedChat, setHasStartedChat] = useState(false)
    const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
    const [showAllFiles, setShowAllFiles] = useState(false)
    const [isStartingChat, setIsStartingChat] = useState(false)
    const [handledUrlFile, setHandledUrlFile] = useState(false)
    const [previewType, setPreviewType] = useState<'none' | 'pdf' | 'image' | 'text' | 'office' | 'unsupported'>('none')
    const [previewText, setPreviewText] = useState("")
    const [previewUrl, setPreviewUrl] = useState<string | null>(null)
    const [previewError, setPreviewError] = useState<string | null>(null)
    const [isPreviewLoading, setIsPreviewLoading] = useState(false)
    const [previewReloadVersion, setPreviewReloadVersion] = useState(0)
    const fileInputRef = useRef<HTMLInputElement>(null)
    const [activeCitation, setActiveCitation] = useState<FileCitation | null>(null)
    const [activeCitationLabel, setActiveCitationLabel] = useState<string | null>(null)
    const [retrievalRecords, setRetrievalRecords] = useState<RetrievalRecordResponse[]>([])
    const [targetPage, setTargetPage] = useState<number | undefined>(undefined)
    const [targetHighlightIndex, setTargetHighlightIndex] = useState<number | undefined>(undefined)
    // Counter that increments on every citation click to force scroll even for repeated clicks
    const scrollTriggerRef = useRef(0)
    const selectedFileId = selectedFile?.id ?? null
    const selectedFileType = selectedFile?.type ?? ''
    const selectedFileName = selectedFile?.name ?? ''

    const highlights = useMemo(() => {
        const filtered = activeCitationLabel
            ? retrievalRecords.filter((record) =>
                record.citation_label === activeCitationLabel &&
                (selectedFileId === null || record.file_id === selectedFileId)
            )
            : []
        const bboxItems = filtered.flatMap(r => parseBBoxJson(r.bbox_json))
        return groupHighlightsByPage(bboxItems)
    }, [retrievalRecords, activeCitationLabel, selectedFileId])

    const loadRetrievalRecords = useCallback(async (messageId: number) => {
        if (!currentChatId) return
        try {
            const records = await fetchRetrievalRecords(currentChatId, messageId)
            setRetrievalRecords(records)
        } catch {
            // Ignore retrieval fetch errors
        }
    }, [currentChatId])

    const handleFileCitationClick = useCallback((citation: FileCitation, messageId?: number) => {
        setActiveCitation(citation)
        setActiveCitationLabel(citation.citation_label)

        const pageNo = citation.page_no ?? undefined
        setTargetPage(pageNo)
        // Increment scroll trigger to force PdfViewer to re-scroll,
        // even when clicking the same citation repeatedly
        scrollTriggerRef.current += 1
        setTargetHighlightIndex(scrollTriggerRef.current)

        if (citation.file_id) {
            const citationFile = availableFiles.find(f => f.id === citation.file_id)
            if (citationFile && citationFile.id !== selectedFile?.id) {
                setSelectedFile(citationFile)
            }
        }

        if (messageId) {
            void loadRetrievalRecords(messageId)
        }
    }, [availableFiles, selectedFile, loadRetrievalRecords])

    const messages = currentChatId ? messagesByChat[currentChatId] : undefined
    const lastAssistantMsgId = messages
        ? [...messages].reverse().find(m => m.role === 'assistant')?.id
        : undefined

    useEffect(() => {
        if (!currentChatId || !hasStartedChat || !lastAssistantMsgId) {
            setRetrievalRecords([])
            setActiveCitationLabel(null)
            return
        }

        void loadRetrievalRecords(lastAssistantMsgId)
    }, [currentChatId, hasStartedChat, lastAssistantMsgId, loadRetrievalRecords])



    useEffect(() => {
        const loadFiles = async () => {
            try {
                await fetchFiles()
            } catch (error) {
                toast.error(error instanceof Error ? error.message : 'Failed to load files')
            }
        }
        void loadFiles()
    }, [fetchFiles])

    useEffect(() => {
        if (!currentChatId) {
            return
        }

        const currentSession = chatSessions.find((session) => session.id === currentChatId)

        if (currentSession?.chatType === 'file') {
            const attachedFiles = files.filter((file) =>
                currentSession.fileIds.includes(file.id)
            )
            const canStartChat = attachedFiles.length > 0
            setHasStartedChat(canStartChat)
            setAvailableFiles(attachedFiles)
            setSelectedFile((previousSelectedFile) =>
                attachedFiles.find((file) => file.id === previousSelectedFile?.id) ||
                attachedFiles[0] ||
                null
            )
            const hasConversationLoaded = messagesByChat[currentChatId] !== undefined
            if (canStartChat && !hasConversationLoaded) {
                void loadConversation(currentChatId)
            }
            if (isStartingChat) {
                setIsStartingChat(false)
            }
            return
        }

        if (!fileIdFromUrl && !isStartingChat) {
            setHasStartedChat(false)
            setAvailableFiles([])
            setSelectedFile(null)
        }
    }, [
        currentChatId,
        chatSessions,
        messagesByChat,
        files,
        fileIdFromUrl,
        isStartingChat,
        loadConversation,
    ])

    useEffect(() => {
        if (!currentChatId && !fileIdFromUrl && !isStartingChat) {
            setHasStartedChat(false)
            setAvailableFiles([])
            setSelectedFile(null)
        }
    }, [currentChatId, fileIdFromUrl, isStartingChat])

    useEffect(() => {
        if (files.length === 0) {
            return
        }
        const fileMap = new Map(files.map((file) => [file.id, file]))

        setAvailableFiles((previousFiles) => {
            if (previousFiles.length === 0) {
                return previousFiles
            }

            const syncedFiles = previousFiles
                .map((file) => fileMap.get(file.id))
                .filter((file): file is FileItem => Boolean(file))

            const hasChanged =
                syncedFiles.length !== previousFiles.length ||
                syncedFiles.some((file, index) => file !== previousFiles[index])

            return hasChanged ? syncedFiles : previousFiles
        })

        setSelectedFile((previousSelectedFile) => {
            if (!previousSelectedFile) {
                return previousSelectedFile
            }
            return fileMap.get(previousSelectedFile.id) || null
        })
    }, [files])

    useEffect(() => {
        if (fileChatNewRequestId === 0) {
            return
        }
        setHasStartedChat(false)
        setAvailableFiles([])
        setSelectedFile(null)
        setShowAllFiles(false)
        setUploadedFiles([])
        setShowUploadDialog(false)
        setShowLibraryDialog(false)
        if (fileInputRef.current) {
            fileInputRef.current.value = ''
        }
    }, [fileChatNewRequestId])

    useEffect(() => {
        if (!fileIdFromUrl || handledUrlFile) {
            return
        }
        const parsedFileId = Number(fileIdFromUrl)
        if (Number.isNaN(parsedFileId)) {
            setHandledUrlFile(true)
            return
        }
        const file = files.find((item) => item.id === parsedFileId)
        if (!file) {
            return
        }

        const startUrlConversation = async () => {
            try {
                setSelectedFile(file)
                setAvailableFiles([file])
                setHasStartedChat(true)
                setIsStartingChat(true)
                await createNewChat('file', {
                    fileIds: [file.id],
                })
                setHandledUrlFile(true)
            } catch (error) {
                setHasStartedChat(false)
                setIsStartingChat(false)
                setHandledUrlFile(true)
                toast.error(
                    error instanceof Error
                        ? error.message
                        : 'Failed to create file conversation'
                )
            }
        }
        void startUrlConversation()
    }, [fileIdFromUrl, files, handledUrlFile, createNewChat])

    useEffect(() => {
        let isActive = true

        const loadPreview = async () => {
            if (!selectedFileId) {
                setPreviewType('none')
                setPreviewText("")
                setPreviewError(null)
                setPreviewUrl(null)
                return
            }

            setIsPreviewLoading(true)
            setPreviewError(null)
            setPreviewText("")
            setPreviewUrl(null)

            try {
                // Get a fresh SAS URL for this file
                const sasUrl = await refreshSasUrl(selectedFileId)
                if (!isActive) return
                if (!sasUrl) {
                    throw new Error('Unable to generate preview URL')
                }

                if (selectedFileType.includes('pdf')) {
                    setPreviewType('pdf')
                    setPreviewUrl(sasUrl)
                } else if (selectedFileType.includes('image')) {
                    setPreviewType('image')
                    setPreviewUrl(sasUrl)
                } else if (
                    selectedFileName.match(/\.(docx|xlsx|pptx)$/i)
                ) {
                    setPreviewType('office')
                    setPreviewUrl(sasUrl)
                } else if (
                    selectedFileType.startsWith('text/') ||
                    selectedFileType.includes('json') ||
                    selectedFileType.includes('csv') ||
                    selectedFileType.includes('xml')
                ) {
                    const response = await fetch(sasUrl)
                    if (!isActive) return
                    if (!response.ok) {
                        throw new Error(`Cannot preview file (${response.status})`)
                    }
                    const textContent = await response.text()
                    if (!isActive) return
                    setPreviewType('text')
                    setPreviewText(textContent.slice(0, 30000))
                } else {
                    setPreviewType('unsupported')
                }
            } catch (error) {
                if (!isActive) {
                    return
                }
                setPreviewType('unsupported')
                setPreviewError(
                    error instanceof Error ? error.message : 'Failed to load preview'
                )
            } finally {
                if (isActive) {
                    setIsPreviewLoading(false)
                }
            }
        }

        void loadPreview()

        return () => {
            isActive = false
        }
    }, [previewReloadVersion, refreshSasUrl, selectedFileId, selectedFileName, selectedFileType])

    const syncConversationFiles = async (nextFiles: FileItem[]) => {
        if (hasStartedChat && currentChatId) {
            await updateConversationFiles(
                currentChatId,
                nextFiles.map((file) => file.id)
            )
        }
    }

    const handleAvailableFileToggle = (file: FileItem) => {
        const exists = availableFiles.some((item) => item.id === file.id)
        const nextFiles = exists
            ? availableFiles.filter((item) => item.id !== file.id)
            : [...availableFiles, file]

        setAvailableFiles(nextFiles)

        if (exists) {
            if (selectedFile?.id === file.id) {
                setSelectedFile(nextFiles[0] || null)
            }
            return
        }

        setSelectedFile(file)
    }

    const openLibraryDialog = () => {
        setPendingLibraryFiles(availableFiles)
        setShowLibraryDialog(true)
    }

    const handleLibraryDialogChange = (open: boolean) => {
        if (open) {
            setPendingLibraryFiles(availableFiles)
            setShowLibraryDialog(true)
            return
        }

        setPendingLibraryFiles(availableFiles)
        setShowLibraryDialog(false)
    }

    const handleLibraryFileToggle = (file: FileItem) => {
        setPendingLibraryFiles((previousFiles) => {
            const exists = previousFiles.some((item) => item.id === file.id)
            return exists
                ? previousFiles.filter((item) => item.id !== file.id)
                : [...previousFiles, file]
        })
    }

    const handleLibraryCancel = () => {
        setPendingLibraryFiles(availableFiles)
        setShowLibraryDialog(false)
    }

    const handleLibraryConfirm = async () => {
        const previousFiles = availableFiles
        const previousSelectedFile = selectedFile
        const nextFiles = pendingLibraryFiles

        setAvailableFiles(nextFiles)
        setSelectedFile((currentSelectedFile) => {
            if (currentSelectedFile && nextFiles.some((file) => file.id === currentSelectedFile.id)) {
                return currentSelectedFile
            }

            if (previousSelectedFile && nextFiles.some((file) => file.id === previousSelectedFile.id)) {
                return previousSelectedFile
            }

            return nextFiles[0] || null
        })

        try {
            await syncConversationFiles(nextFiles)
            setShowLibraryDialog(false)
        } catch (error) {
            setAvailableFiles(previousFiles)
            setSelectedFile(previousSelectedFile)
            toast.error(
                error instanceof Error
                    ? error.message
                    : 'Failed to update files for this conversation'
            )
        }
    }

    const handleStartChat = async () => {
        if (availableFiles.length > 0) {
            try {
                setIsStartingChat(true)
                setHasStartedChat(true)
                await createNewChat('file', {
                    fileIds: availableFiles.map((file) => file.id),
                })
                toast.success('File conversation created')
            } catch (error) {
                setHasStartedChat(false)
                setIsStartingChat(false)
                toast.error(
                    error instanceof Error
                        ? error.message
                        : 'Failed to create file conversation'
                )
            }
        }
    }

    const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            const filesArray = Array.from(e.target.files)
            // Append new files to existing files instead of replacing
            setUploadedFiles(prev => [...prev, ...filesArray])
        }
    }

    const handleUploadConfirm = async () => {
        if (uploadedFiles.length > 0) {
            try {
                const createdFiles = await uploadFiles(uploadedFiles)
                const mergedFilesMap = new Map<number, FileItem>()
                availableFiles.forEach((file) => mergedFilesMap.set(file.id, file))
                createdFiles.forEach((file) => mergedFilesMap.set(file.id, file))
                const nextFiles = Array.from(mergedFilesMap.values())

                setAvailableFiles(nextFiles)
                if (!selectedFile && nextFiles.length > 0) {
                    setSelectedFile(nextFiles[0])
                }
                await syncConversationFiles(nextFiles)
                toast.success(`Uploaded ${createdFiles.length} file${createdFiles.length > 1 ? 's' : ''}`)

                setShowUploadDialog(false)
                setUploadedFiles([])
                if (fileInputRef.current) {
                    fileInputRef.current.value = ''
                }
            } catch (error) {
                toast.error(error instanceof Error ? error.message : 'Upload failed')
            }
        }
    }

    const handleUploadCancel = () => {
        if (!isUploading) {
            setShowUploadDialog(false)
            setUploadedFiles([])
            if (fileInputRef.current) {
                fileInputRef.current.value = ''
            }
        }
    }

    const handleDownloadSelectedFile = async () => {
        if (!selectedFile) {
            return
        }
        try {
            await downloadFile(selectedFile.id)
            toast.success('Download started')
        } catch (error) {
            toast.error(error instanceof Error ? error.message : 'Download failed')
        }
    }

    const handleRefreshFileLibrary = async () => {
        try {
            await fetchFiles()
        } catch (error) {
            toast.error(error instanceof Error ? error.message : 'Failed to refresh files')
            return
        }
        if (!currentChatId || !hasStartedChat) {
            setPreviewReloadVersion((value) => value + 1)
            return
        }

        const latestStoreState = useFileStore.getState()
        const latestChatState = useChatStore.getState()
        const activeSession = latestChatState.chatSessions.find(
            (session) => session.id === currentChatId
        )
        if (!activeSession) {
            return
        }

        const attachedFiles = latestStoreState.files.filter((file) =>
            activeSession.fileIds.includes(file.id)
        )
        setAvailableFiles(attachedFiles)
        setSelectedFile(
            attachedFiles.find((file) => file.id === selectedFile?.id) ||
            attachedFiles[0] ||
            null
        )
        setPreviewReloadVersion((value) => value + 1)
        toast.success('File list refreshed')
    }

    const handleRemoveSelectedFromConversation = async () => {
        if (!selectedFile) {
            return
        }
        const previousFiles = availableFiles
        const previousSelectedFile = selectedFile
        const nextFiles = availableFiles.filter((file) => file.id !== selectedFile.id)
        setAvailableFiles(nextFiles)
        setSelectedFile(nextFiles[0] || null)
        try {
            await syncConversationFiles(nextFiles)
            toast.success('Removed file from this conversation')
        } catch (error) {
            setAvailableFiles(previousFiles)
            setSelectedFile(previousSelectedFile)
            toast.error(
                error instanceof Error
                    ? error.message
                    : 'Failed to update files for this conversation'
            )
        }
    }

    const getFileTypeDisplay = (type: string) => {
        if (type.includes('pdf')) return 'PDF'
        if (type.includes('sheet') || type.includes('excel')) return 'XLSX'
        if (type.includes('document') || type.includes('word')) return 'DOCX'
        if (type.includes('image')) return 'IMG'
        return 'FILE'
    }

    const getFileTypeColor = (type: string) => {
        if (type.includes('pdf')) return 'bg-red-50 text-red-600'
        if (type.includes('sheet') || type.includes('excel')) return 'bg-green-50 text-green-600'
        if (type.includes('document') || type.includes('word')) return 'bg-blue-50 text-blue-600'
        if (type.includes('image')) return 'bg-purple-50 text-purple-600'
        return 'bg-gray-50 text-gray-600'
    }

    const getIngestionLabel = (file: FileItem) => {
        if (file.ingestionStatus === 'completed') {
            return 'Completed'
        }
        if (file.ingestionStatus === 'failed') {
            return 'Failed'
        }
        if (
            file.ingestionStatus === 'embedding' ||
            file.ingestionStatus === 'parsing' ||
            file.ingestionStatus === 'chunking' ||
            file.ingestionStatus === 'indexing' ||
            file.ingestionStatus === 'processing'
        ) {
            return 'Processing'
        }
        return 'Pending'
    }

    const getIngestionTextClass = (file: FileItem) => {
        if (file.ingestionStatus === 'completed') return 'text-emerald-600'
        if (file.ingestionStatus === 'failed') return 'text-red-600'
        if (
            file.ingestionStatus === 'embedding' ||
            file.ingestionStatus === 'parsing' ||
            file.ingestionStatus === 'chunking' ||
            file.ingestionStatus === 'indexing' ||
            file.ingestionStatus === 'processing'
        ) return 'text-amber-600'
        return 'text-slate-500'
    }

    const formatSize = (bytes: number) => {
        if (bytes === 0) return '0 Bytes'
        const k = 1024
        const sizes = ['Bytes', 'KB', 'MB', 'GB']
        const i = Math.floor(Math.log(bytes) / Math.log(k))
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }

    // Sort files by upload date (newest first) and limit display
    const sortedFiles = [...files].sort((a, b) => b.uploadedAt - a.uploadedAt)
    const displayedFiles = showAllFiles ? sortedFiles : sortedFiles.slice(0, 5)
    const hasMoreFiles = sortedFiles.length > 5

    // Show file selection screen if chat hasn't started
    if (!hasStartedChat) {
        return (
            <div className="flex h-full w-full items-center justify-center bg-surface p-8">
                <Card className="w-full max-w-2xl bg-white rounded-xl shadow-lg border-border flex flex-col max-h-[90vh]">
                    {/* Header - Fixed */}
                    <div className="p-8 pb-6 shrink-0">
                        <div className="text-center">
                            <div className="h-16 w-16 bg-tech-gradient rounded-[1.6rem] flex items-center justify-center mx-auto mb-4 shadow-[0_20px_45px_rgba(18,130,79,0.24)] ring-1 ring-emerald-500/20">
                                <ScanSearch className="h-8 w-8 text-white" />
                            </div>
                            <h2 className="font-display text-2xl font-bold text-text-primary mb-2">Chat with File</h2>
                            <p className="text-text-muted">Select files to start chatting or upload new ones</p>
                        </div>
                    </div>

                    {/* Scrollable Content */}
                    <div className="flex-1 overflow-y-auto px-8">
                        <div className="grid grid-cols-2 gap-4 mb-6">
                            <Button
                                type="button"
                                variant="outline"
                                className="h-32 flex flex-col gap-3 border-2 border-dashed border-border hover:border-primary hover:bg-primary/5 rounded-xl"
                                onClick={() => setShowUploadDialog(true)}
                            >
                                <div className="h-12 w-12 bg-primary/10 rounded-full flex items-center justify-center">
                                    <Upload className="h-6 w-6 text-primary" />
                                </div>
                                <div>
                                    <p className="font-medium text-text-primary">Upload New File</p>
                                    <p className="text-xs text-text-muted mt-1">PDF, DOCX, XLSX, etc.</p>
                                </div>
                            </Button>

                            <Button
                                type="button"
                                variant="outline"
                                className="h-32 flex flex-col gap-3 border-2 border-dashed border-border hover:border-primary hover:bg-primary/5 rounded-xl"
                                onClick={openLibraryDialog}
                            >
                                <div className="h-12 w-12 bg-primary/10 rounded-full flex items-center justify-center">
                                    <FolderOpen className="h-6 w-6 text-primary" />
                                </div>
                                <div>
                                    <p className="font-medium text-text-primary">From Library</p>
                                    <p className="text-xs text-text-muted mt-1">{files.length} files available</p>
                                </div>
                            </Button>
                        </div>

                        {/* Selected Files List */}
                        {availableFiles.length > 0 && (
                            <div className="mb-6">
                                <h3 className="text-sm font-medium text-text-primary mb-3">Selected Files ({availableFiles.length})</h3>
                                <div className="space-y-2 max-h-64 overflow-y-auto">
                                    {availableFiles.map((file) => (
                                        <div key={file.id} className="flex items-center gap-3 p-3 bg-surface rounded-lg border border-border">
                                            <div className={`h-10 w-10 rounded-lg flex items-center justify-center shrink-0 ${getFileTypeColor(file.type)}`}>
                                                <span className="text-xs font-bold">{getFileTypeDisplay(file.type)}</span>
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="font-medium text-sm truncate">{file.name}</div>
                                                <div className="text-xs text-text-muted">{formatSize(file.size)}</div>
                                                <div className={`text-[11px] ${getIngestionTextClass(file)}`}>
                                                    {getIngestionLabel(file)}
                                                </div>
                                            </div>
                                            <Button
                                                type="button"
                                                variant="ghost"
                                                size="icon"
                                                className="h-8 w-8 rounded-lg"
                                                onClick={() => handleAvailableFileToggle(file)}
                                            >
                                                <X className="h-4 w-4" />
                                            </Button>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Recent Files - Show 5 newest */}
                        {files.length > 0 && (
                            <div className="mb-6">
                                <div className="flex items-center justify-between mb-3">
                                    <h3 className="text-sm font-medium text-text-primary">Recent Files</h3>
                                    {hasMoreFiles && !showAllFiles && (
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            size="sm"
                                            className="text-xs text-primary"
                                            onClick={() => setShowAllFiles(true)}
                                        >
                                            View All ({sortedFiles.length})
                                        </Button>
                                    )}
                                </div>
                                <div className="grid grid-cols-2 gap-2">
                                    {displayedFiles.map((file) => {
                                        const isSelected = availableFiles.some(f => f.id === file.id)
                                        return (
                                            <Button
                                                key={file.id}
                                                type="button"
                                                variant="outline"
                                                aria-pressed={isSelected}
                                                className={`h-auto p-3 justify-start rounded-lg transition-colors ${isSelected ? 'bg-primary/10 border-primary ring-1 ring-primary/30' : ''}`}
                                                onClick={() => handleAvailableFileToggle(file)}
                                            >
                                                <div className="flex items-center gap-2 w-full">
                                                    <div className={`h-8 w-8 rounded-md flex items-center justify-center shrink-0 ${getFileTypeColor(file.type)}`}>
                                                        <span className="text-xs font-bold">{getFileTypeDisplay(file.type)}</span>
                                                    </div>
                                                    <div className="flex-1 min-w-0 text-left">
                                                        <div className="font-medium text-xs truncate">{file.name}</div>
                                                        <div className="text-[10px] text-text-muted">{formatSize(file.size)}</div>
                                                        <div className={`text-[10px] ${getIngestionTextClass(file)}`}>
                                                            {getIngestionLabel(file)}
                                                        </div>
                                                    </div>
                                                    {isSelected && (
                                                        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-white">
                                                            <Check className="h-3.5 w-3.5" />
                                                        </div>
                                                    )}
                                                </div>
                                            </Button>
                                        )
                                    })}
                                </div>
                                {showAllFiles && hasMoreFiles && (
                                    <Button
                                        type="button"
                                        variant="outline"
                                        size="sm"
                                        className="w-full mt-2 rounded-lg"
                                        onClick={() => setShowAllFiles(false)}
                                    >
                                        <ChevronUp className="h-4 w-4 mr-2" />
                                        Show Less
                                    </Button>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Footer - Fixed */}
                    <div className="p-8 pt-4 border-t border-border shrink-0 bg-white">
                        <Button
                            type="button"
                            className="w-full bg-primary hover:bg-primary-hover text-white rounded-lg py-6 text-base font-medium"
                            onClick={() => void handleStartChat()}
                            disabled={availableFiles.length === 0}
                        >
                            Start Chat with {availableFiles.length} File{availableFiles.length !== 1 ? 's' : ''}
                        </Button>
                    </div>
                </Card>

                {/* Library Selection Dialog */}
                <Dialog open={showLibraryDialog} onOpenChange={handleLibraryDialogChange}>
                    <DialogContent className="bg-white rounded-xl max-w-2xl">
                        <DialogHeader>
                            <DialogTitle>Select Files from Library</DialogTitle>
                            <DialogDescription>Choose one or more files to chat with</DialogDescription>
                        </DialogHeader>
                        <div className="max-h-96 overflow-y-auto py-4">
                            {files.length === 0 ? (
                                <div className="text-center py-8 text-text-muted">
                                    <FolderOpen className="h-12 w-12 mx-auto mb-3 opacity-50" />
                                    <p>No files uploaded yet</p>
                                    <p className="text-xs mt-1">Upload files first to select them</p>
                                </div>
                            ) : (
                                <div className="grid gap-2">
                                    {sortedFiles.map((file) => {
                                        const isSelected = pendingLibraryFiles.some(f => f.id === file.id)
                                        return (
                                            <Button
                                                key={file.id}
                                                type="button"
                                                variant="outline"
                                                aria-pressed={isSelected}
                                                className={`w-full justify-start h-auto p-3 rounded-lg hover:bg-primary/10 hover:border-primary transition-colors ${isSelected ? 'bg-primary/10 border-primary ring-1 ring-primary/30' : ''}`}
                                                onClick={() => handleLibraryFileToggle(file)}
                                            >
                                                <div className="flex items-center gap-3 w-full">
                                                    <div className={`h-10 w-10 rounded-lg flex items-center justify-center shrink-0 ${getFileTypeColor(file.type)}`}>
                                                        <span className="text-xs font-bold">{getFileTypeDisplay(file.type)}</span>
                                                    </div>
                                                    <div className="flex-1 min-w-0 text-left">
                                                        <div className="font-medium text-sm truncate">{file.name}</div>
                                                        <div className="text-xs text-text-muted">
                                                            {formatSize(file.size)} • Uploaded {new Date(file.uploadedAt).toLocaleDateString()}
                                                        </div>
                                                        <div className={`text-xs ${getIngestionTextClass(file)}`}>
                                                            {getIngestionLabel(file)}
                                                        </div>
                                                    </div>
                                                    {isSelected && (
                                                        <div className="inline-flex shrink-0 items-center gap-1 rounded-full bg-primary/10 px-2 py-1 text-xs font-medium text-primary">
                                                            <Check className="h-3.5 w-3.5" />
                                                            Selected
                                                        </div>
                                                    )}
                                                </div>
                                            </Button>
                                        )
                                    })}
                                </div>
                            )}
                        </div>
                        <div className="flex justify-end gap-2 pt-4 border-t border-border">
                            <Button
                                type="button"
                                variant="outline"
                                className="rounded-lg"
                                onClick={handleLibraryCancel}
                            >
                                Cancel
                            </Button>
                            <Button
                                type="button"
                                className="bg-primary hover:bg-primary-hover text-white rounded-lg"
                                onClick={() => void handleLibraryConfirm()}
                            >
                                Done
                            </Button>
                        </div>
                    </DialogContent>
                </Dialog>

                {/* Upload Dialog */}
                <Dialog open={showUploadDialog} onOpenChange={(open) => !isUploading && setShowUploadDialog(open)}>
                    <DialogContent className="bg-white rounded-xl max-w-md sm:max-w-lg">
                        <DialogHeader>
                            <DialogTitle>Upload Files</DialogTitle>
                            <DialogDescription>
                                {isUploading ? 'Processing your files...' : 'Select one or more files from your computer'}
                            </DialogDescription>
                        </DialogHeader>
                        <div className="py-4 space-y-4 max-h-[60vh] overflow-y-auto">
                            <div className="border-2 border-dashed border-border rounded-lg p-6 text-center hover:border-primary transition-colors">
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    onChange={handleFileInputChange}
                                    className="hidden"
                                    id="file-upload"
                                    disabled={isUploading}
                                    multiple
                                />
                                <label htmlFor="file-upload" className={isUploading ? 'cursor-not-allowed' : 'cursor-pointer'}>
                                    <div className="flex flex-col items-center gap-2">
                                        <div className="h-12 w-12 bg-primary/10 rounded-full flex items-center justify-center">
                                            <Upload className="h-6 w-6 text-primary" />
                                        </div>
                                        <div>
                                            <p className="text-sm font-medium text-text-primary">Click to select files</p>
                                            <p className="text-xs text-text-muted mt-1">PDF, DOCX, XLSX, images, etc. (Multiple allowed)</p>
                                        </div>
                                    </div>
                                </label>
                            </div>

                            {uploadedFiles.length > 0 && (
                                <div className="space-y-2">
                                    <p className="text-sm font-medium text-text-primary">
                                        {uploadedFiles.length} file{uploadedFiles.length > 1 ? 's' : ''} selected
                                    </p>
                                    {uploadedFiles.map((file, index) => (
                                        <div key={index} className="flex items-center gap-3 p-3 bg-surface rounded-lg border border-border">
                                            <div className="h-10 w-10 bg-primary/10 rounded-lg flex items-center justify-center shrink-0">
                                                {isUploading ? (
                                                    <div className="animate-spin h-5 w-5 border-2 border-primary border-t-transparent rounded-full" />
                                                ) : (
                                                    <FileText className="h-5 w-5 text-primary" />
                                                )}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm font-medium truncate">{file.name}</p>
                                                <p className="text-xs text-text-muted">
                                                    {isUploading ? 'Processing...' : formatSize(file.size)}
                                                </p>
                                            </div>
                                            {!isUploading && (
                                                <Button
                                                    type="button"
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-8 w-8 rounded-lg"
                                                    onClick={() => {
                                                        setUploadedFiles(prev => prev.filter((_, i) => i !== index))
                                                    }}
                                                >
                                                    <X className="h-4 w-4" />
                                                </Button>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                        <div className="flex justify-end gap-2">
                            <Button
                                type="button"
                                variant="outline"
                                onClick={handleUploadCancel}
                                className="rounded-lg"
                                disabled={isUploading}
                            >
                                Cancel
                            </Button>
                            <Button
                                type="button"
                                className="bg-primary hover:bg-primary-hover text-white rounded-lg"
                                onClick={() => void handleUploadConfirm()}
                                disabled={uploadedFiles.length === 0 || isUploading}
                            >
                                {isUploading ? (
                                    <>
                                        <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full mr-2" />
                                        Uploading...
                                    </>
                                ) : (
                                    `Upload ${uploadedFiles.length > 0 ? uploadedFiles.length : ''} File${uploadedFiles.length > 1 ? 's' : ''}`
                                )}
                            </Button>
                        </div>
                    </DialogContent>
                </Dialog>
            </div>
        )
    }

    // Main chat interface (shown after file selection)
    return (
        <div className="flex h-full w-full overflow-hidden bg-white">
            {/* Left Panel: Chat */}
            <div className="w-1/2 h-full border-r border-border flex flex-col bg-white">
                <div className="flex-1 overflow-hidden">
                    <ChatInterface onFileCitationClick={handleFileCitationClick} />
                </div>
            </div>

            {/* Right Panel: File Viewer */}
            <div className="w-1/2 h-full flex flex-col bg-surface">
                {/* Sticky Header with File Selector */}
                <div className="h-14 border-b border-border flex items-center px-4 justify-between bg-white sticky top-0 z-10 shadow-sm">
                    <div className="flex items-center gap-3">
                        <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <Button type="button" variant="outline" className="gap-2 border-border bg-white hover:bg-surface rounded-lg">
                                    {selectedFile ? (
                                        <>
                                            <div className={`h-6 w-6 rounded-md flex items-center justify-center ${getFileTypeColor(selectedFile.type)}`}>
                                                <span className="text-[10px] font-bold">{getFileTypeDisplay(selectedFile.type)}</span>
                                            </div>
                                            <div className="text-left">
                                                <div className="font-medium text-sm truncate max-w-[150px]">{selectedFile.name}</div>
                                                <div className={`text-[10px] ${getIngestionTextClass(selectedFile)}`}>
                                                    {getIngestionLabel(selectedFile)}
                                                </div>
                                            </div>
                                        </>
                                    ) : (
                                        <span className="text-sm text-text-muted">No file selected</span>
                                    )}
                                    <ChevronDown className="h-4 w-4 ml-2" />
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="start" className="w-64 bg-white border-border shadow-lg rounded-lg">
                                {availableFiles.map((file) => (
                                    <DropdownMenuItem
                                        key={file.id}
                                        onClick={() => setSelectedFile(file)}
                                        className="flex items-center gap-3 p-3 cursor-pointer rounded-md"
                                    >
                                        <div className={`h-8 w-8 rounded-md flex items-center justify-center shrink-0 ${getFileTypeColor(file.type)}`}>
                                            <span className="text-xs font-bold">{getFileTypeDisplay(file.type)}</span>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="font-medium text-sm truncate">{file.name}</div>
                                            <div className="text-xs text-text-muted">{formatSize(file.size)}</div>
                                            <div className={`text-[11px] ${getIngestionTextClass(file)}`}>
                                                {getIngestionLabel(file)}
                                            </div>
                                        </div>
                                    </DropdownMenuItem>
                                ))}
                                <DropdownMenuSeparator />
                                <DropdownMenuItem
                                    className="cursor-pointer rounded-md text-primary focus:text-primary font-medium"
                                    onClick={openLibraryDialog}
                                >
                                    <FolderOpen className="mr-2 h-4 w-4" />
                                    Select from Library
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                    </div>
                    <div className="flex items-center gap-1">
                        <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 rounded-lg"
                            onClick={() => void handleDownloadSelectedFile()}
                            disabled={!selectedFile}
                        >
                            <Download className="h-4 w-4" />
                        </Button>
                        <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 rounded-lg"
                            onClick={() => void handleRefreshFileLibrary()}
                        >
                            <RefreshCw className="h-4 w-4" />
                        </Button>
                        <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-red-600 hover:text-red-700 rounded-lg"
                            onClick={() => void handleRemoveSelectedFromConversation()}
                            disabled={!selectedFile}
                        >
                            <Trash2 className="h-4 w-4" />
                        </Button>
                    </div>
                </div>

                {/* File Content Preview */}
                <div className="flex-1 p-6 overflow-auto">
                    <Card className="h-full shadow-sm border-border rounded-xl bg-white overflow-hidden">
                        {!selectedFile ? null : isPreviewLoading ? (
                            <div className="h-full flex flex-col items-center justify-center gap-3">
                                <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" />
                                <p className="text-sm text-text-muted">Loading preview...</p>
                            </div>
                        ) : previewType === 'pdf' && previewUrl ? (
                            <div className="h-full flex flex-col">
                                {/* Active Citation Indicator */}
                                {activeCitation && activeCitation.file_id === selectedFileId && (
                                    <div className="flex items-center gap-2 px-4 py-2 bg-amber-50 border-b border-amber-200 shrink-0">
                                        <div className="flex items-center gap-2 flex-1">
                                            <span className="inline-flex items-center justify-center min-w-[2rem] h-5 text-[10px] font-bold text-white bg-amber-500 rounded-full px-1.5">
                                                [{activeCitation.citation_label}]
                                            </span>
                                            <span className="text-xs text-amber-800 font-medium">
                                                {activeCitation.file_name}
                                                {activeCitation.page_no ? ` — Page ${activeCitation.page_no}` : ''}
                                            </span>
                                        </div>
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            size="icon"
                                            className="h-5 w-5 rounded text-amber-600 hover:text-amber-800 hover:bg-amber-100"
                                            onClick={() => setActiveCitation(null)}
                                        >
                                            <X className="h-3 w-3" />
                                        </Button>
                                    </div>
                                )}
                                <Suspense
                                    fallback={
                                        <div className="flex flex-1 items-center justify-center bg-surface">
                                            <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" />
                                        </div>
                                    }
                                >
                                    <PdfViewer
                                        key={`${selectedFileId}-${previewUrl}`}
                                        url={previewUrl}
                                        highlights={highlights}
                                        targetPage={targetPage}
                                        targetHighlightIndex={targetHighlightIndex}
                                    />
                                </Suspense>
                            </div>
                        ) : previewType === 'image' && previewUrl ? (
                            <div className="h-full w-full flex items-center justify-center bg-surface p-4">
                                <img
                                    src={previewUrl}
                                    alt={selectedFile.name}
                                    className="max-h-full max-w-full object-contain rounded-lg shadow-sm"
                                />
                            </div>
                        ) : previewType === 'text' ? (
                            <div className="h-full overflow-auto p-4">
                                <div className="mb-3">
                                    <h3 className="font-medium text-text-primary text-base">{selectedFile.name}</h3>
                                    <p className="text-xs text-text-muted">Showing first 30,000 characters</p>
                                </div>
                                <pre className="text-xs leading-relaxed whitespace-pre-wrap break-words text-text-primary bg-surface p-3 rounded-lg border border-border">
                                    {previewText || "This file has no text content."}
                                </pre>
                            </div>
                        ) : previewType === 'office' && previewUrl ? (
                            <iframe
                                src={`https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(previewUrl)}`}
                                className="h-full w-full border-0"
                                title={selectedFile.name}
                            />
                        ) : (
                            <div className="h-full flex flex-col items-center justify-center text-center space-y-4 p-6">
                                <div className="h-20 w-20 bg-surface rounded-full flex items-center justify-center mx-auto">
                                    <FileText className="h-10 w-10 text-text-muted" />
                                </div>
                                <div>
                                    <h3 className="font-medium text-text-primary text-lg">{selectedFile.name}</h3>
                                    <p className="text-sm text-text-muted max-w-xs mx-auto mt-2">
                                        {getFileTypeDisplay(selectedFile.type)} Preview Unavailable
                                    </p>
                                    {previewError && (
                                        <p className="text-xs text-red-500 max-w-xs mx-auto mt-1">
                                            {previewError}
                                        </p>
                                    )}
                                </div>
                                <div className="flex flex-col gap-2">
                                    <Button
                                        type="button"
                                        variant="outline"
                                        className="border-border rounded-lg"
                                        onClick={() => void handleDownloadSelectedFile()}
                                    >
                                        Download to View
                                    </Button>
                                    {availableFiles.length > 1 && (
                                        <p className="text-xs text-text-muted">
                                            {availableFiles.length} files available in this chat
                                        </p>
                                    )}
                                </div>
                            </div>
                        )}
                    </Card>
                </div>
            </div>
            {/* Library Selection Dialog */}
            <Dialog open={showLibraryDialog} onOpenChange={handleLibraryDialogChange}>
                <DialogContent className="bg-white rounded-xl max-w-2xl">
                    <DialogHeader>
                        <DialogTitle>Select Files from Library</DialogTitle>
                        <DialogDescription>Choose one or more files to chat with</DialogDescription>
                    </DialogHeader>
                    <div className="max-h-96 overflow-y-auto py-4">
                        {files.length === 0 ? (
                            <div className="text-center py-8 text-text-muted">
                                <FolderOpen className="h-12 w-12 mx-auto mb-3 opacity-50" />
                                <p>No files uploaded yet</p>
                                <p className="text-xs mt-1">Upload files first to select them</p>
                            </div>
                        ) : (
                            <div className="grid gap-2">
                                {sortedFiles.map((file) => {
                                    const isSelected = pendingLibraryFiles.some(f => f.id === file.id)
                                    return (
                                        <Button
                                            key={file.id}
                                            type="button"
                                            variant="outline"
                                            aria-pressed={isSelected}
                                            className={`w-full justify-start h-auto p-3 rounded-lg hover:bg-primary/10 hover:border-primary transition-colors ${isSelected ? 'bg-primary/10 border-primary ring-1 ring-primary/30' : ''}`}
                                            onClick={() => handleLibraryFileToggle(file)}
                                        >
                                            <div className="flex items-center gap-3 w-full">
                                                <div className={`h-10 w-10 rounded-lg flex items-center justify-center shrink-0 ${getFileTypeColor(file.type)}`}>
                                                    <span className="text-xs font-bold">{getFileTypeDisplay(file.type)}</span>
                                                </div>
                                                <div className="flex-1 min-w-0 text-left">
                                                    <div className="font-medium text-sm truncate">{file.name}</div>
                                                    <div className="text-xs text-text-muted">
                                                        {formatSize(file.size)} • Uploaded {new Date(file.uploadedAt).toLocaleDateString()}
                                                    </div>
                                                    <div className={`text-xs ${getIngestionTextClass(file)}`}>
                                                        {getIngestionLabel(file)}
                                                    </div>
                                                </div>
                                                {isSelected && (
                                                    <div className="inline-flex shrink-0 items-center gap-1 rounded-full bg-primary/10 px-2 py-1 text-xs font-medium text-primary">
                                                        <Check className="h-3.5 w-3.5" />
                                                        Selected
                                                    </div>
                                                )}
                                            </div>
                                        </Button>
                                    )
                                })}
                            </div>
                        )}
                    </div>
                    <div className="flex justify-end gap-2 pt-4 border-t border-border">
                        <Button
                            type="button"
                            variant="outline"
                            className="rounded-lg"
                            onClick={handleLibraryCancel}
                        >
                            Cancel
                        </Button>
                        <Button
                            type="button"
                            className="bg-primary hover:bg-primary-hover text-white rounded-lg"
                            onClick={() => void handleLibraryConfirm()}
                        >
                            Done
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Upload Dialog */}
            <Dialog open={showUploadDialog} onOpenChange={(open) => !isUploading && setShowUploadDialog(open)}>
                <DialogContent className="bg-white rounded-xl max-w-md sm:max-w-lg">
                    <DialogHeader>
                        <DialogTitle>Upload Files</DialogTitle>
                        <DialogDescription>
                            {isUploading ? 'Processing your files...' : 'Select one or more files from your computer'}
                        </DialogDescription>
                    </DialogHeader>
                    <div className="py-4 space-y-4 max-h-[60vh] overflow-y-auto">
                        <div className="border-2 border-dashed border-border rounded-lg p-6 text-center hover:border-primary transition-colors">
                            <input
                                ref={fileInputRef}
                                type="file"
                                onChange={handleFileInputChange}
                                className="hidden"
                                id="file-upload-chat"
                                disabled={isUploading}
                                multiple
                            />
                            <label htmlFor="file-upload-chat" className={isUploading ? 'cursor-not-allowed' : 'cursor-pointer'}>
                                <div className="flex flex-col items-center gap-2">
                                    <div className="h-12 w-12 bg-primary/10 rounded-full flex items-center justify-center">
                                        <Upload className="h-6 w-6 text-primary" />
                                    </div>
                                    <div>
                                        <p className="text-sm font-medium text-text-primary">Click to select files</p>
                                        <p className="text-xs text-text-muted mt-1">PDF, DOCX, XLSX, images, etc. (Multiple allowed)</p>
                                    </div>
                                </div>
                            </label>
                        </div>

                        {uploadedFiles.length > 0 && (
                            <div className="space-y-2">
                                <p className="text-sm font-medium text-text-primary">
                                    {uploadedFiles.length} file{uploadedFiles.length > 1 ? 's' : ''} selected
                                </p>
                                {uploadedFiles.map((file, index) => (
                                    <div key={index} className="flex items-center gap-3 p-3 bg-surface rounded-lg border border-border">
                                        <div className="h-10 w-10 bg-primary/10 rounded-lg flex items-center justify-center shrink-0">
                                            {isUploading ? (
                                                <div className="animate-spin h-5 w-5 border-2 border-primary border-t-transparent rounded-full" />
                                            ) : (
                                                <FileText className="h-5 w-5 text-primary" />
                                            )}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium truncate">{file.name}</p>
                                            <p className="text-xs text-text-muted">
                                                {isUploading ? 'Processing...' : formatSize(file.size)}
                                            </p>
                                        </div>
                                        {!isUploading && (
                                            <Button
                                                type="button"
                                                variant="ghost"
                                                size="icon"
                                                className="h-8 w-8 rounded-lg"
                                                onClick={() => {
                                                    setUploadedFiles(prev => prev.filter((_, i) => i !== index))
                                                }}
                                            >
                                                <X className="h-4 w-4" />
                                            </Button>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                    <div className="flex justify-end gap-2">
                        <Button
                            type="button"
                            variant="outline"
                            onClick={handleUploadCancel}
                            className="rounded-lg"
                            disabled={isUploading}
                        >
                            Cancel
                        </Button>
                        <Button
                            type="button"
                            className="bg-primary hover:bg-primary-hover text-white rounded-lg"
                            onClick={() => void handleUploadConfirm()}
                            disabled={uploadedFiles.length === 0 || isUploading}
                        >
                            {isUploading ? (
                                <>
                                    <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full mr-2" />
                                    Uploading...
                                </>
                            ) : (
                                `Upload ${uploadedFiles.length > 0 ? uploadedFiles.length : ''} File${uploadedFiles.length > 1 ? 's' : ''}`
                            )}
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    )
}
