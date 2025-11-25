import { ChatInterface } from "@/components/chat/ChatInterface"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { FileText, Download, Trash2, RefreshCw, ChevronDown, FolderOpen, Upload, X, ChevronUp } from "lucide-react"
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
import { useFileStore } from "@/store/file-store"
import { useState, useEffect, useRef } from "react"
import { useSearchParams } from "react-router-dom"
import { useChatStore } from "@/store/chat-store"

export default function ChatWithFilePage() {
    const [searchParams] = useSearchParams()
    const fileIdFromUrl = searchParams.get('fileId')
    const { files, addFile } = useFileStore()
    const { createNewChat, currentChatId, getCurrentMessages } = useChatStore()

    const [selectedFile, setSelectedFile] = useState<any>(null)
    const [showUploadDialog, setShowUploadDialog] = useState(false)
    const [showLibraryDialog, setShowLibraryDialog] = useState(false)
    const [availableFiles, setAvailableFiles] = useState<any[]>([])
    const [hasStartedChat, setHasStartedChat] = useState(false)
    const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
    const [showAllFiles, setShowAllFiles] = useState(false)
    const [isUploading, setIsUploading] = useState(false)
    const [previousChatId, setPreviousChatId] = useState<string | null>(null)
    const [isStartingChat, setIsStartingChat] = useState(false)
    const fileInputRef = useRef<HTMLInputElement>(null)

    // Watch for chat changes - handle both new chat and selecting existing chat
    useEffect(() => {
        if (currentChatId && currentChatId !== previousChatId) {
            const currentMessages = getCurrentMessages()

            // If selecting an existing chat with messages, show the chat interface
            if (currentMessages.length > 0) {
                setHasStartedChat(true)
            }
            // If this is a new empty chat AND user didn't manually start chat, reset to selection screen
            else if (!fileIdFromUrl && !isStartingChat) {
                setHasStartedChat(false)
                setAvailableFiles([])
                setSelectedFile(null)
            }

            setPreviousChatId(currentChatId)

            // Reset the starting flag after processing
            if (isStartingChat) {
                setIsStartingChat(false)
            }
        }
    }, [currentChatId, previousChatId, getCurrentMessages, fileIdFromUrl, isStartingChat])

    useEffect(() => {
        // If fileId in URL, filter to show only that file, create new chat, and start chat immediately
        if (fileIdFromUrl) {
            const file = files.find(f => f.id === fileIdFromUrl)
            if (file) {
                setSelectedFile(file)
                setAvailableFiles([file])
                setHasStartedChat(true)
                setIsStartingChat(true)
                createNewChat('file')
            }
        }
    }, [fileIdFromUrl, files])

    const handleFileSelect = (file: any) => {
        const exists = availableFiles.some(f => f.id === file.id)
        if (!exists) {
            setAvailableFiles(prev => [...prev, file])
        }
        setSelectedFile(file)
    }

    const handleStartChat = () => {
        if (availableFiles.length > 0) {
            setIsStartingChat(true)  // Set flag before creating chat
            setHasStartedChat(true)
            createNewChat('file')
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
            setIsUploading(true)

            // Simulate API call - in real app, this would be actual file upload
            try {
                await new Promise(resolve => setTimeout(resolve, 2000)) // 2 second delay

                // Process all files
                uploadedFiles.forEach(uploadedFile => {
                    const newFile = {
                        id: `file-${Date.now()}-${Math.random()}`,
                        name: uploadedFile.name,
                        type: uploadedFile.type,
                        size: uploadedFile.size,
                        uploadedAt: Date.now()
                    }
                    addFile(newFile)
                    handleFileSelect(newFile)
                })

                // Reset and close dialog
                setShowUploadDialog(false)
                setUploadedFiles([])
                if (fileInputRef.current) {
                    fileInputRef.current.value = ''
                }
            } catch (error) {
                console.error('Upload failed:', error)
            } finally {
                setIsUploading(false)
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
                            <div className="h-16 w-16 bg-tech-gradient rounded-2xl flex items-center justify-center mx-auto mb-4">
                                <FileText className="h-8 w-8 text-white" />
                            </div>
                            <h2 className="text-2xl font-bold text-text-primary mb-2">Chat with File</h2>
                            <p className="text-text-muted">Select files to start chatting or upload new ones</p>
                        </div>
                    </div>

                    {/* Scrollable Content */}
                    <div className="flex-1 overflow-y-auto px-8">
                        <div className="grid grid-cols-2 gap-4 mb-6">
                            <Button
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
                                variant="outline"
                                className="h-32 flex flex-col gap-3 border-2 border-dashed border-border hover:border-primary hover:bg-primary/5 rounded-xl"
                                onClick={() => setShowLibraryDialog(true)}
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
                                            </div>
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-8 w-8 rounded-lg"
                                                onClick={() => {
                                                    setAvailableFiles(prev => prev.filter(f => f.id !== file.id))
                                                    if (selectedFile?.id === file.id) {
                                                        setSelectedFile(availableFiles[0] || null)
                                                    }
                                                }}
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
                                                variant="outline"
                                                className={`h-auto p-3 justify-start rounded-lg ${isSelected ? 'bg-primary/10 border-primary' : ''}`}
                                                onClick={() => handleFileSelect(file)}
                                            >
                                                <div className="flex items-center gap-2 w-full">
                                                    <div className={`h-8 w-8 rounded-md flex items-center justify-center shrink-0 ${getFileTypeColor(file.type)}`}>
                                                        <span className="text-xs font-bold">{getFileTypeDisplay(file.type)}</span>
                                                    </div>
                                                    <div className="flex-1 min-w-0 text-left">
                                                        <div className="font-medium text-xs truncate">{file.name}</div>
                                                        <div className="text-[10px] text-text-muted">{formatSize(file.size)}</div>
                                                    </div>
                                                    {isSelected && (
                                                        <div className="text-xs text-primary font-medium">✓</div>
                                                    )}
                                                </div>
                                            </Button>
                                        )
                                    })}
                                </div>
                                {showAllFiles && hasMoreFiles && (
                                    <Button
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
                            className="w-full bg-primary hover:bg-primary-hover text-white rounded-lg py-6 text-base font-medium"
                            onClick={handleStartChat}
                            disabled={availableFiles.length === 0}
                        >
                            Start Chat with {availableFiles.length} File{availableFiles.length !== 1 ? 's' : ''}
                        </Button>
                    </div>
                </Card>

                {/* Library Selection Dialog */}
                <Dialog open={showLibraryDialog} onOpenChange={setShowLibraryDialog}>
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
                                        const isSelected = availableFiles.some(f => f.id === file.id)
                                        return (
                                            <Button
                                                key={file.id}
                                                variant="outline"
                                                className={`w-full justify-start h-auto p-3 rounded-lg hover:bg-primary/10 hover:border-primary ${isSelected ? 'bg-primary/10 border-primary' : ''}`}
                                                onClick={() => handleFileSelect(file)}
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
                                                    </div>
                                                    {isSelected && (
                                                        <div className="text-xs text-primary font-medium">✓ Selected</div>
                                                    )}
                                                </div>
                                            </Button>
                                        )
                                    })}
                                </div>
                            )}
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
                                variant="outline"
                                onClick={handleUploadCancel}
                                className="rounded-lg"
                                disabled={isUploading}
                            >
                                Cancel
                            </Button>
                            <Button
                                className="bg-primary hover:bg-primary-hover text-white rounded-lg"
                                onClick={handleUploadConfirm}
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
                <div className="h-14 border-b border-border flex items-center px-4 justify-between bg-surface">
                    <div className="flex items-center gap-2">
                        <div className="p-1.5 bg-primary/10 rounded-lg">
                            <FileText className="h-4 w-4 text-primary" />
                        </div>
                        <span className="font-medium text-sm text-text-primary">Chat with File Mode</span>
                    </div>
                </div>
                <div className="flex-1 overflow-hidden">
                    <ChatInterface />
                </div>
            </div>

            {/* Right Panel: File Viewer */}
            <div className="w-1/2 h-full flex flex-col bg-surface">
                {/* Sticky Header with File Selector */}
                <div className="h-14 border-b border-border flex items-center px-4 justify-between bg-white sticky top-0 z-10 shadow-sm">
                    <div className="flex items-center gap-3">
                        <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <Button variant="outline" className="gap-2 border-border bg-white hover:bg-surface rounded-lg">
                                    {selectedFile ? (
                                        <>
                                            <div className={`h-6 w-6 rounded-md flex items-center justify-center ${getFileTypeColor(selectedFile.type)}`}>
                                                <span className="text-[10px] font-bold">{getFileTypeDisplay(selectedFile.type)}</span>
                                            </div>
                                            <div className="text-left">
                                                <div className="font-medium text-sm truncate max-w-[150px]">{selectedFile.name}</div>
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
                                        </div>
                                    </DropdownMenuItem>
                                ))}
                                <DropdownMenuSeparator />
                                <DropdownMenuItem
                                    className="cursor-pointer rounded-md text-primary focus:text-primary font-medium"
                                    onClick={() => setShowLibraryDialog(true)}
                                >
                                    <FolderOpen className="mr-2 h-4 w-4" />
                                    Select from Library
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                    </div>
                    <div className="flex items-center gap-1">
                        <Button variant="ghost" size="icon" className="h-8 w-8 rounded-lg">
                            <Download className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8 rounded-lg">
                            <RefreshCw className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-red-600 hover:text-red-700 rounded-lg">
                            <Trash2 className="h-4 w-4" />
                        </Button>
                    </div>
                </div>

                {/* File Content Preview */}
                <div className="flex-1 p-6 overflow-auto">
                    <Card className="h-full shadow-sm border-border rounded-xl flex flex-col items-center justify-center bg-white">
                        {selectedFile ? (
                            <div className="text-center space-y-4">
                                <div className="h-20 w-20 bg-surface rounded-full flex items-center justify-center mx-auto">
                                    <FileText className="h-10 w-10 text-text-muted" />
                                </div>
                                <div>
                                    <h3 className="font-medium text-text-primary text-lg">{selectedFile.name}</h3>
                                    <p className="text-sm text-text-muted max-w-xs mx-auto mt-2">
                                        {getFileTypeDisplay(selectedFile.type)} Preview Unavailable
                                    </p>
                                    <p className="text-xs text-text-muted max-w-xs mx-auto mt-1">
                                        In a real app, a renderer would display the document here.
                                    </p>
                                </div>
                                <div className="flex flex-col gap-2">
                                    <Button variant="outline" className="border-border rounded-lg">
                                        Download to View
                                    </Button>
                                    {availableFiles.length > 1 && (
                                        <p className="text-xs text-text-muted">
                                            {availableFiles.length} files available in this chat
                                        </p>
                                    )}
                                </div>
                            </div>
                        ) : null}
                    </Card>
                </div>
            </div>
            {/* Library Selection Dialog */}
            <Dialog open={showLibraryDialog} onOpenChange={setShowLibraryDialog}>
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
                                    const isSelected = availableFiles.some(f => f.id === file.id)
                                    return (
                                        <Button
                                            key={file.id}
                                            variant="outline"
                                            className={`w-full justify-start h-auto p-3 rounded-lg hover:bg-primary/10 hover:border-primary ${isSelected ? 'bg-primary/10 border-primary' : ''}`}
                                            onClick={() => handleFileSelect(file)}
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
                                                </div>
                                                {isSelected && (
                                                    <div className="text-xs text-primary font-medium">✓ Selected</div>
                                                )}
                                            </div>
                                        </Button>
                                    )
                                })}
                            </div>
                        )}
                    </div>
                    <div className="flex justify-end pt-4 border-t border-border">
                        <Button
                            className="bg-primary hover:bg-primary-hover text-white rounded-lg"
                            onClick={() => setShowLibraryDialog(false)}
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
                            variant="outline"
                            onClick={handleUploadCancel}
                            className="rounded-lg"
                            disabled={isUploading}
                        >
                            Cancel
                        </Button>
                        <Button
                            className="bg-primary hover:bg-primary-hover text-white rounded-lg"
                            onClick={handleUploadConfirm}
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
