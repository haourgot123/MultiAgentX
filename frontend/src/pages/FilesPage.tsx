import { useFileStore } from "@/store/file-store"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { FileText, Trash2, Upload, MoreVertical, ArrowUpDown, Filter, Eye, Edit2, X } from "lucide-react"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
    DropdownMenuSeparator,
    DropdownMenuLabel,
} from "@/components/ui/dropdown-menu"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { useState, useRef } from "react"
import { useNavigate } from "react-router-dom"

export default function FilesPage() {
    const { files, removeFile, addFile } = useFileStore()
    const navigate = useNavigate()
    const [sortOrder, setSortOrder] = useState("date-desc")
    const [filterType, setFilterType] = useState("all")
    const [selectedFile, setSelectedFile] = useState<any>(null)
    const [showDetailsDialog, setShowDetailsDialog] = useState(false)
    const [showRenameDialog, setShowRenameDialog] = useState(false)
    const [showUploadDialog, setShowUploadDialog] = useState(false)
    const [newFileName, setNewFileName] = useState("")
    const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
    const [isUploading, setIsUploading] = useState(false)
    const fileInputRef = useRef<HTMLInputElement>(null)

    const formatSize = (bytes: number) => {
        if (bytes === 0) return '0 Bytes'
        const k = 1024
        const sizes = ['Bytes', 'KB', 'MB', 'GB']
        const i = Math.floor(Math.log(bytes) / Math.log(k))
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }

    const sortedFiles = [...files]
        .filter(file => filterType === "all" || file.type.includes(filterType))
        .sort((a, b) => {
            if (sortOrder === "date-desc") return b.uploadedAt - a.uploadedAt
            if (sortOrder === "date-asc") return a.uploadedAt - b.uploadedAt
            if (sortOrder === "name-asc") return a.name.localeCompare(b.name)
            if (sortOrder === "name-desc") return b.name.localeCompare(a.name)
            if (sortOrder === "size-desc") return b.size - a.size
            if (sortOrder === "size-asc") return a.size - b.size
            return 0
        })

    const handleUploadClick = () => {
        setShowUploadDialog(true)
    }

    const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            const filesArray = Array.from(e.target.files)
            setUploadedFiles(prev => [...prev, ...filesArray])
        }
    }

    const handleUploadConfirm = async () => {
        if (uploadedFiles.length > 0) {
            setIsUploading(true)

            try {
                await new Promise(resolve => setTimeout(resolve, 2000))

                uploadedFiles.forEach(uploadedFile => {
                    const newFile = {
                        id: `file-${Date.now()}-${Math.random()}`,
                        name: uploadedFile.name,
                        type: uploadedFile.type,
                        size: uploadedFile.size,
                        uploadedAt: Date.now()
                    }
                    addFile(newFile)
                })

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

    const handleViewDetails = (file: any) => {
        setSelectedFile(file)
        setShowDetailsDialog(true)
    }

    const handleRename = (file: any) => {
        setSelectedFile(file)
        setNewFileName(file.name)
        setShowRenameDialog(true)
    }

    const confirmRename = () => {
        setShowRenameDialog(false)
        setSelectedFile(null)
        setNewFileName("")
    }

    const handleDelete = (fileId: string) => {
        if (confirm('Are you sure you want to delete this file?')) {
            removeFile(fileId)
        }
    }

    const handleOpenInChat = (file: any) => {
        navigate(`/chat-file?fileId=${file.id}`)
    }

    const sortOptions = [
        { value: "date-desc", label: "Newest First" },
        { value: "date-asc", label: "Oldest First" },
        { value: "name-asc", label: "Name (A-Z)" },
        { value: "name-desc", label: "Name (Z-A)" },
        { value: "size-desc", label: "Size (Largest)" },
        { value: "size-asc", label: "Size (Smallest)" },
    ]

    const filterOptions = [
        { value: "all", label: "All Files" },
        { value: "pdf", label: "PDF" },
        { value: "csv", label: "CSV/Excel" },
        { value: "image", label: "Images" },
    ]

    return (
        <div className="flex-1 h-full p-8 overflow-auto bg-surface">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-primary">
                        File Management
                    </h1>
                    <p className="text-text-muted mt-1">
                        Manage your uploaded documents and data.
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="outline" className="gap-2 rounded-lg">
                                <Filter className="h-4 w-4" />
                                Filter: {filterOptions.find(f => f.value === filterType)?.label}
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="bg-white rounded-lg">
                            <DropdownMenuLabel>Filter by Type</DropdownMenuLabel>
                            <DropdownMenuSeparator />
                            {filterOptions.map((option) => (
                                <DropdownMenuItem
                                    key={option.value}
                                    onClick={() => setFilterType(option.value)}
                                    className={`cursor-pointer rounded-md ${filterType === option.value ? 'bg-primary/10 text-primary' : ''}`}
                                >
                                    {option.label}
                                </DropdownMenuItem>
                            ))}
                        </DropdownMenuContent>
                    </DropdownMenu>

                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="outline" className="gap-2 rounded-lg">
                                <ArrowUpDown className="h-4 w-4" />
                                Sort: {sortOptions.find(s => s.value === sortOrder)?.label}
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="bg-white rounded-lg">
                            <DropdownMenuLabel>Sort by</DropdownMenuLabel>
                            <DropdownMenuSeparator />
                            {sortOptions.map((option) => (
                                <DropdownMenuItem
                                    key={option.value}
                                    onClick={() => setSortOrder(option.value)}
                                    className={`cursor-pointer rounded-md ${sortOrder === option.value ? 'bg-primary/10 text-primary' : ''}`}
                                >
                                    {option.label}
                                </DropdownMenuItem>
                            ))}
                        </DropdownMenuContent>
                    </DropdownMenu>

                    <Button className="bg-primary hover:bg-primary-hover text-white shadow-md rounded-lg" onClick={handleUploadClick}>
                        <Upload className="mr-2 h-4 w-4" />
                        Upload File
                    </Button>
                </div>
            </div>

            {sortedFiles.length === 0 ? (
                <Card className="shadow-sm border-border rounded-xl bg-white">
                    <CardContent className="flex flex-col items-center justify-center py-16">
                        <div className="h-20 w-20 bg-surface rounded-full flex items-center justify-center mb-4">
                            <FileText className="h-10 w-10 text-text-muted" />
                        </div>
                        <h3 className="text-lg font-semibold text-text-primary mb-2">No files uploaded yet</h3>
                        <p className="text-sm text-text-muted mb-6 text-center max-w-sm">
                            Start by uploading your first file. Supported formats include PDF, DOCX, XLSX, and more.
                        </p>
                        <Button className="bg-primary hover:bg-primary-hover text-white rounded-lg" onClick={handleUploadClick}>
                            <Upload className="mr-2 h-4 w-4" />
                            Upload Your First File
                        </Button>
                    </CardContent>
                </Card>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {sortedFiles.map((file) => (
                        <Card key={file.id} className="shadow-sm border-border hover:shadow-md transition-shadow rounded-xl bg-white">
                            <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
                                <div className="flex items-center gap-3 flex-1 min-w-0">
                                    <div className="h-10 w-10 bg-primary/10 rounded-lg flex items-center justify-center shrink-0">
                                        <FileText className="h-5 w-5 text-primary" />
                                    </div>
                                    <div className="min-w-0 flex-1">
                                        <CardTitle className="text-base font-semibold truncate text-text-primary">
                                            {file.name}
                                        </CardTitle>
                                        <CardDescription className="text-xs text-text-muted">
                                            {formatSize(file.size)}
                                        </CardDescription>
                                    </div>
                                </div>
                                <DropdownMenu>
                                    <DropdownMenuTrigger asChild>
                                        <Button variant="ghost" size="icon" className="h-8 w-8 rounded-lg">
                                            <MoreVertical className="h-4 w-4" />
                                        </Button>
                                    </DropdownMenuTrigger>
                                    <DropdownMenuContent align="end" className="bg-white rounded-lg">
                                        <DropdownMenuItem onClick={() => handleViewDetails(file)} className="cursor-pointer rounded-md">
                                            <Eye className="mr-2 h-4 w-4" />
                                            View Details
                                        </DropdownMenuItem>
                                        <DropdownMenuItem onClick={() => handleRename(file)} className="cursor-pointer rounded-md">
                                            <Edit2 className="mr-2 h-4 w-4" />
                                            Rename
                                        </DropdownMenuItem>
                                        <DropdownMenuItem onClick={() => handleOpenInChat(file)} className="cursor-pointer rounded-md">
                                            <FileText className="mr-2 h-4 w-4" />
                                            Open in Chat
                                        </DropdownMenuItem>
                                        <DropdownMenuSeparator />
                                        <DropdownMenuItem onClick={() => handleDelete(file.id)} className="text-red-600 cursor-pointer rounded-md">
                                            <Trash2 className="mr-2 h-4 w-4" />
                                            Delete
                                        </DropdownMenuItem>
                                    </DropdownMenuContent>
                                </DropdownMenu>
                            </CardHeader>
                            <CardContent>
                                <div className="text-xs text-text-muted mt-2 flex items-center justify-between">
                                    <span>Uploaded {new Date(file.uploadedAt).toLocaleDateString()}</span>
                                    <span className="uppercase text-[10px] font-semibold bg-surface px-1.5 py-0.5 rounded-md border border-border">
                                        {file.type.split('/')[1] || 'FILE'}
                                    </span>
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}

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
                                id="file-upload-management"
                                disabled={isUploading}
                                multiple
                            />
                            <label htmlFor="file-upload-management" className={isUploading ? 'cursor-not-allowed' : 'cursor-pointer'}>
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
                    <DialogFooter>
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
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* View Details Dialog */}
            <Dialog open={showDetailsDialog} onOpenChange={setShowDetailsDialog}>
                <DialogContent className="bg-white rounded-xl">
                    <DialogHeader>
                        <DialogTitle>File Details</DialogTitle>
                        <DialogDescription>Information about the selected file</DialogDescription>
                    </DialogHeader>
                    {selectedFile && (
                        <div className="space-y-3 py-4">
                            <div>
                                <Label className="text-text-muted">Name</Label>
                                <p className="text-text-primary font-medium">{selectedFile.name}</p>
                            </div>
                            <div>
                                <Label className="text-text-muted">Type</Label>
                                <p className="text-text-primary">{selectedFile.type}</p>
                            </div>
                            <div>
                                <Label className="text-text-muted">Size</Label>
                                <p className="text-text-primary">{formatSize(selectedFile.size)}</p>
                            </div>
                            <div>
                                <Label className="text-text-muted">Uploaded</Label>
                                <p className="text-text-primary">{new Date(selectedFile.uploadedAt).toLocaleString()}</p>
                            </div>
                        </div>
                    )}
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowDetailsDialog(false)} className="rounded-lg">Close</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Rename Dialog */}
            <Dialog open={showRenameDialog} onOpenChange={setShowRenameDialog}>
                <DialogContent className="bg-white rounded-xl">
                    <DialogHeader>
                        <DialogTitle>Rename File</DialogTitle>
                        <DialogDescription>Enter a new name for the file</DialogDescription>
                    </DialogHeader>
                    <div className="py-4">
                        <Label htmlFor="filename">File Name</Label>
                        <Input
                            id="filename"
                            value={newFileName}
                            onChange={(e) => setNewFileName(e.target.value)}
                            className="mt-2 rounded-lg"
                        />
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowRenameDialog(false)} className="rounded-lg">Cancel</Button>
                        <Button className="bg-primary hover:bg-primary-hover text-white rounded-lg" onClick={confirmRename}>Rename</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    )
}
