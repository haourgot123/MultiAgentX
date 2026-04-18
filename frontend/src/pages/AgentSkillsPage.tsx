import { useEffect, useMemo, useRef, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { useAgentSkillsStore, type Skill } from "@/store/agent-skills-store"
import { useAuthStore } from "@/store/auth-store"
import { useFileStore, type FileItem } from "@/store/file-store"
import { FileViewer } from "@/components/FileViewer"

import { API_BASE_URL } from "@/lib/api"
import { toast } from "sonner"
import JSZip from "jszip"
import {
    Bot,
    Boxes,
    CheckCircle2,
    Cpu,
    Download,
    Eye,
    FileText,
    FolderOpen,
    Loader2,
    Paperclip,
    Play,
    RefreshCw,
    Sparkles,
    Trash2,
    Upload,
    User,
    X,
    XCircle,
} from "lucide-react"

type OutputFile = {
    name: string
    size: number
    sandbox_index: number
    download_url: string
    blob_url?: string | null
}

type ExecutionRun = {
    id: number
    prompt: string
    output: string
    progress: string[]
    liveStatus: string | null
    status: 'running' | 'done' | 'error'
    error: string | null
    attachedFiles: FileItem[]
    usedSkills: Skill[]
    outputFiles?: OutputFile[]
    createdAt: number
}

type LocalSandboxExecution = {
    sandboxIndex: number
    prompt: string
    startedAt: number
    completedAt: number | null
    skillNames: string[]
}

const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const units = ['B', 'KB', 'MB', 'GB']
    const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
    const value = bytes / 1024 ** index
    return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`
}

const formatTimestamp = (timestamp: number | null): string => {
    if (!timestamp) {
        return 'No activity yet'
    }

    return new Intl.DateTimeFormat('vi-VN', {
        hour: '2-digit',
        minute: '2-digit',
        day: '2-digit',
        month: '2-digit',
    }).format(timestamp)
}

const getSandboxStatusIcon = (status: string) => {
    switch (status) {
        case 'ready':
            return <CheckCircle2 className="h-4 w-4 text-emerald-500" />
        case 'busy':
            return <Loader2 className="h-4 w-4 animate-spin text-amber-500" />
        case 'error':
            return <XCircle className="h-4 w-4 text-red-500" />
        default:
            return <Cpu className="h-4 w-4 text-slate-400" />
    }
}

const getRunStatusLabel = (status: ExecutionRun['status']) => {
    if (status === 'running') return 'Running'
    if (status === 'error') return 'Failed'
    return 'Completed'
}

export default function AgentSkillsPage() {
    const {
        skills,
        sandboxes,
        isLoading,
        isUploading: isUploadingSkill,
        isExecuting,
        executionProgress,
        executionOutput,
        currentConversationId,
        executionRunsByConversation,
        artifactsByConversation,
        lastExecutionError,
        fetchConversations,
        loadConversation,
        createConversation,
        fetchSkills,
        uploadSkill,
        deleteSkill,
        toggleSkillSelection,
        fetchSandboxes,
        executeSkills,
    } = useAgentSkillsStore()
    const {
        files,
        fetchFiles,
        uploadFiles,
        isUploading: isUploadingChatFile,
    } = useFileStore()

    const [pendingSkillUpload, setPendingSkillUpload] = useState<File | null>(null)
    const [isSkillDragActive, setIsSkillDragActive] = useState(false)
    const [isZippingFolder, setIsZippingFolder] = useState(false)
    const [userMessage, setUserMessage] = useState("")
    const [attachedFiles, setAttachedFiles] = useState<FileItem[]>([])
    const [selectedRunId, setSelectedRunId] = useState<number | null>(null)
    const [localSandboxExecution, setLocalSandboxExecution] = useState<LocalSandboxExecution | null>(null)
    const [viewingFile, setViewingFile] = useState<{ url: string; filename: string } | null>(null)

    const skillUploadInputRef = useRef<HTMLInputElement>(null)
    const skillFolderInputRef = useRef<HTMLInputElement>(null)
    const chatUploadInputRef = useRef<HTMLInputElement>(null)
    const chatScrollRef = useRef<HTMLDivElement>(null)



    const selectedSkills = useMemo(
        () => skills.filter((skill) => skill.isSelected),
        [skills]
    )
    const readySandboxes = useMemo(
        () => sandboxes.filter((sandbox) => sandbox.status === 'ready'),
        [sandboxes]
    )
    const sortedSkills = useMemo(
        () => [...skills].sort((left, right) => right.createdAt - left.createdAt),
        [skills]
    )
    const skillMap = useMemo(
        () => new Map(skills.map((skill) => [skill.id, skill])),
        [skills]
    )
    const sandboxProgress = useMemo(() => {
        if (!localSandboxExecution) {
            return null
        }

        if (lastExecutionError) {
            return {
                progress: 100,
                status: 'error' as const,
            }
        }

        if (!isExecuting) {
            return {
                progress: 100,
                status: 'ready' as const,
            }
        }

        const normalizedProgress = executionProgress.join(' ').toLowerCase()
        if (executionOutput.trim().length > 0) {
            return {
                progress: 88,
                status: 'busy' as const,
            }
        }

        if (normalizedProgress.includes('executing')) {
            return {
                progress: 62,
                status: 'busy' as const,
            }
        }

        if (normalizedProgress.includes('creating')) {
            return {
                progress: 24,
                status: 'busy' as const,
            }
        }

        return {
            progress: 12,
            status: 'busy' as const,
        }
    }, [executionOutput, executionProgress, isExecuting, lastExecutionError, localSandboxExecution])
    const displaySandboxes = useMemo(() => sandboxes.map((sandbox) => {
        if (!localSandboxExecution || sandbox.sandboxIndex !== localSandboxExecution.sandboxIndex) {
            return sandbox
        }

        return {
            ...sandbox,
            status: sandboxProgress?.status || sandbox.status,
            progress: sandboxProgress?.progress ?? sandbox.progress,
            taskDescription: localSandboxExecution.prompt,
            startedAt: localSandboxExecution.startedAt,
            completedAt: localSandboxExecution.completedAt,
        }
    }), [localSandboxExecution, sandboxProgress, sandboxes])
    const currentConversationRuns = useMemo(() => {
        if (!currentConversationId) {
            return []
        }

        const artifacts = artifactsByConversation[currentConversationId] || []
        const artifactsByMessageId = artifacts.reduce<Map<number, OutputFile[]>>((map, artifact) => {
            if (!artifact.message_id) {
                return map
            }

            const artifactOutputFile: OutputFile = {
                name: artifact.file_name,
                size: artifact.size,
                sandbox_index: -1,
                download_url: artifact.download_url || `/skills/artifacts/${artifact.id}/download`,
                blob_url: artifact.download_url,
            }

            const existingFiles = map.get(artifact.message_id) || []
            map.set(artifact.message_id, [...existingFiles, artifactOutputFile])
            return map
        }, new Map<number, OutputFile[]>())

        return (executionRunsByConversation[currentConversationId] || []).map((run) => ({
            id: run.id,
            prompt: run.prompt,
            output: run.output,
            progress: run.progress,
            liveStatus: run.liveStatus,
            status: run.status,
            error: run.error,
            attachedFiles: run.attachedFileIds
                .map((fileId) => files.find((file) => file.id === fileId))
                .filter((file): file is FileItem => Boolean(file)),
            usedSkills: run.skillIds
                .map((skillId) => skillMap.get(skillId))
                .filter((skill): skill is Skill => Boolean(skill)),
            outputFiles:
                run.outputFiles && run.outputFiles.length > 0
                    ? run.outputFiles
                    : (
                        run.assistantMessageId
                            ? artifactsByMessageId.get(run.assistantMessageId)
                            : undefined
                    ),
            createdAt: run.createdAt,
        }))
    }, [artifactsByConversation, currentConversationId, executionRunsByConversation, files, skillMap])

    useEffect(() => {
        if (!currentConversationId) {
            return
        }

        if (Object.prototype.hasOwnProperty.call(executionRunsByConversation, currentConversationId)) {
            return
        }

        void loadConversation(currentConversationId).catch((error) => {
            if (!useAuthStore.getState().isAuthenticated) return
            toast.error(error instanceof Error ? error.message : 'Failed to load Agent Skills conversation')
        })
    }, [currentConversationId, executionRunsByConversation, loadConversation])

    useEffect(() => {
        const loadData = async () => {
            try {
                await Promise.all([
                    fetchSkills(),
                    fetchSandboxes(),
                    fetchFiles(),
                ])
                const loadedConversations = await fetchConversations()
                const activeConversationId = useAgentSkillsStore.getState().currentConversationId
                const conversationToLoad =
                    activeConversationId &&
                    loadedConversations.some((conversation) => conversation.id === activeConversationId)
                        ? activeConversationId
                        : loadedConversations[0]?.id

                if (conversationToLoad) {
                    await loadConversation(conversationToLoad)
                }
            } catch (error) {
                if (!useAuthStore.getState().isAuthenticated) return
                toast.error(error instanceof Error ? error.message : 'Failed to load Agent Skills workspace')
            }
        }

        void loadData()
    }, [fetchConversations, fetchFiles, fetchSandboxes, fetchSkills, loadConversation])



    useEffect(() => {
        if (attachedFiles.length === 0) {
            return
        }

        const fileMap = new Map(files.map((file) => [file.id, file]))
        setAttachedFiles((currentFiles) => currentFiles.map((file) => fileMap.get(file.id) || file))
    }, [attachedFiles.length, files])

    const hasMarkedCompleteRef = useRef(false)
    useEffect(() => {
        if (!localSandboxExecution) {
            hasMarkedCompleteRef.current = false
            return
        }

        if (isExecuting) {
            return
        }

        if (hasMarkedCompleteRef.current) {
            return
        }

        hasMarkedCompleteRef.current = true
        setLocalSandboxExecution((currentExecution) => {
            if (!currentExecution) {
                return currentExecution
            }

            return {
                ...currentExecution,
                completedAt: currentExecution.completedAt ?? Date.now(),
            }
        })
    }, [isExecuting])

    const prevRunsLengthRef = useRef(currentConversationRuns.length)
    useEffect(() => {
        if (!chatScrollRef.current) {
            return
        }

        const runsLength = currentConversationRuns.length
        const hasNewRuns = runsLength > prevRunsLengthRef.current
        prevRunsLengthRef.current = runsLength

        if (hasNewRuns) {
            chatScrollRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' })
        }
    }, [currentConversationRuns])

    useEffect(() => {
        if (selectedRunId === null) {
            return
        }

        const targetElement = document.getElementById(`run-${selectedRunId}`)
        if (!targetElement) {
            return
        }

        targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, [selectedRunId])

    const validateSkillMdContent = (content: string): string | null => {
        const trimmed = content.trimStart()
        if (!trimmed.startsWith('---')) {
            return 'SKILL.md must start with a YAML frontmatter block (---)'
        }
        const parts = trimmed.split('---')
        if (parts.length < 3) {
            return 'SKILL.md has invalid frontmatter — missing closing ---'
        }
        const frontmatter = parts[1]
        const nameMatch = frontmatter.match(/^name:\s*["']?(.+?)["']?\s*$/m)
        const descMatch = frontmatter.match(/^description:\s*["']?(.+?)["']?\s*$/m)
        if (!nameMatch?.[1]?.trim()) {
            return 'SKILL.md frontmatter must include a non-empty "name" field'
        }
        if (!descMatch?.[1]?.trim()) {
            return 'SKILL.md frontmatter must include a non-empty "description" field'
        }
        return null
    }

    const validateSkillMdInFiles = async (files: File[]): Promise<string | null> => {
        const skillMd = files.find((f) => {
            const filename = (f.webkitRelativePath || f.name).split('/').pop()
            return filename === 'SKILL.md'
        })
        if (!skillMd) return 'Folder must contain a SKILL.md file'
        const content = await skillMd.text()
        return validateSkillMdContent(content)
    }

    const validateSkillMdInZip = async (file: File): Promise<string | null> => {
        try {
            const zip = await JSZip.loadAsync(file)
            const paths = Object.keys(zip.files)
            const skillMdPath = paths.find((p) => !zip.files[p].dir && p.split('/').pop() === 'SKILL.md')
            if (!skillMdPath) return 'Zip must contain a SKILL.md file'
            const content = await zip.files[skillMdPath].async('string')
            return validateSkillMdContent(content)
        } catch {
            return 'Failed to read zip file'
        }
    }

    const handleSkillCandidate = async (file: File | null) => {
        if (!file) return

        if (!file.name.endsWith('.md') && !file.name.endsWith('.zip')) {
            toast.error('Only .md and .zip files are supported for Agent Skills')
            return
        }

        if (file.name.endsWith('.md')) {
            if (file.name !== 'SKILL.md') {
                toast.error('The uploaded .md file must be named SKILL.md')
                return
            }
            const content = await file.text()
            const error = validateSkillMdContent(content)
            if (error) {
                toast.error(error)
                return
            }
        }

        if (file.name.endsWith('.zip')) {
            const error = await validateSkillMdInZip(file)
            if (error) {
                toast.error(error)
                return
            }
        }

        setPendingSkillUpload(file)
    }

    const zipFolderFiles = async (files: FileList): Promise<File | null> => {
        if (files.length === 0) return null
        setIsZippingFolder(true)
        try {
            const zip = new JSZip()
            const paths = Array.from(files)
            // Find common root prefix so zip structure starts at the folder level
            const firstPath = paths[0].webkitRelativePath || paths[0].name
            const rootPrefix = firstPath.split('/')[0]
            for (const file of paths) {
                const relativePath = file.webkitRelativePath || file.name
                // Strip the top-level folder name so inner structure is preserved
                const zipPath = relativePath.startsWith(rootPrefix + '/')
                    ? relativePath.slice(rootPrefix.length + 1)
                    : relativePath
                if (zipPath) {
                    zip.file(zipPath, file)
                }
            }
            const blob = await zip.generateAsync({ type: 'blob' })
            return new File([blob], `${rootPrefix}.zip`, { type: 'application/zip' })
        } catch {
            toast.error('Failed to package folder')
            return null
        } finally {
            setIsZippingFolder(false)
        }
    }

    const handleSkillFileInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        void handleSkillCandidate(event.target.files?.[0] || null)
        event.target.value = ''
    }

    const handleSkillFolderInputChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const files = event.target.files
        if (!files || files.length === 0) return
        const validationError = await validateSkillMdInFiles(Array.from(files))
        if (validationError) {
            toast.error(validationError)
            event.target.value = ''
            return
        }
        const zipped = await zipFolderFiles(files)
        if (zipped) setPendingSkillUpload(zipped)
        event.target.value = ''
    }

    const readDroppedFolder = async (entry: FileSystemDirectoryEntry): Promise<File[]> => {
        const files: File[] = []
        const readEntries = (dirReader: FileSystemDirectoryReader): Promise<FileSystemEntry[]> =>
            new Promise((resolve) => dirReader.readEntries(resolve))
        const readFile = (fileEntry: FileSystemFileEntry): Promise<File> =>
            new Promise((resolve) => fileEntry.file(resolve))
        const traverse = async (dirEntry: FileSystemDirectoryEntry, path: string) => {
            const reader = dirEntry.createReader()
            let batch: FileSystemEntry[]
            do {
                batch = await readEntries(reader)
                for (const child of batch) {
                    const childPath = path ? `${path}/${child.name}` : child.name
                    if (child.isFile) {
                        const file = await readFile(child as FileSystemFileEntry)
                        Object.defineProperty(file, 'webkitRelativePath', { value: `${dirEntry.name}/${childPath}` })
                        files.push(file)
                    } else if (child.isDirectory) {
                        await traverse(child as FileSystemDirectoryEntry, childPath)
                    }
                }
            } while (batch.length > 0)
        }
        await traverse(entry, '')
        return files
    }

    const handleSkillDrop = async (event: React.DragEvent<HTMLLabelElement>) => {
        event.preventDefault()
        setIsSkillDragActive(false)

        const items = event.dataTransfer.items
        if (items && items.length > 0) {
            const firstEntry = items[0].webkitGetAsEntry?.()
            if (firstEntry?.isDirectory) {
                setIsZippingFolder(true)
                try {
                    const files = await readDroppedFolder(firstEntry as FileSystemDirectoryEntry)
                    if (files.length === 0) {
                        toast.error('Folder is empty')
                        return
                    }
                    const validationError = await validateSkillMdInFiles(files)
                    if (validationError) {
                        toast.error(validationError)
                        return
                    }
                    const zip = new JSZip()
                    for (const file of files) {
                        const relativePath = file.webkitRelativePath || file.name
                        const rootPrefix = relativePath.split('/')[0]
                        const zipPath = relativePath.startsWith(rootPrefix + '/')
                            ? relativePath.slice(rootPrefix.length + 1)
                            : relativePath
                        if (zipPath) zip.file(zipPath, file)
                    }
                    const blob = await zip.generateAsync({ type: 'blob' })
                    const zipFile = new File([blob], `${firstEntry.name}.zip`, { type: 'application/zip' })
                    setPendingSkillUpload(zipFile)
                } catch {
                    toast.error('Failed to package folder')
                } finally {
                    setIsZippingFolder(false)
                }
                return
            }
        }
        void handleSkillCandidate(event.dataTransfer.files?.[0] || null)
    }

    const handleSkillUploadConfirm = async () => {
        if (!pendingSkillUpload) {
            return
        }

        try {
            await uploadSkill(pendingSkillUpload)
            toast.success('Skill uploaded successfully')
            setPendingSkillUpload(null)
        } catch (error) {
            toast.error(error instanceof Error ? error.message : 'Failed to upload skill')
        }
    }

    const handleSkillSelection = async (skillId: number, checked: boolean) => {
        try {
            await toggleSkillSelection(skillId, checked)
        } catch (error) {
            toast.error(error instanceof Error ? error.message : 'Failed to update skill selection')
        }
    }

    const handleDeleteSkill = async (skillId: number) => {
        try {
            await deleteSkill(skillId)
            toast.success('Skill removed')
        } catch (error) {
            toast.error(error instanceof Error ? error.message : 'Failed to delete skill')
        }
    }

    const handleChatFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const filesToUpload = event.target.files ? Array.from(event.target.files) : []
        if (filesToUpload.length === 0) {
            return
        }

        try {
            const uploaded = await uploadFiles(filesToUpload)
            setAttachedFiles((currentFiles) => {
                const existingIds = new Set(currentFiles.map((file) => file.id))
                return [...currentFiles, ...uploaded.filter((file) => !existingIds.has(file.id))]
            })
            toast.success(`Uploaded ${uploaded.length} file${uploaded.length > 1 ? 's' : ''}`)
        } catch (error) {
            toast.error(error instanceof Error ? error.message : 'Failed to upload files')
        } finally {
            event.target.value = ''
        }
    }

    const handleRemoveAttachedFile = (fileId: number) => {
        setAttachedFiles((currentFiles) => currentFiles.filter((file) => file.id !== fileId))
    }

    const handleExecute = async () => {
        const prompt = userMessage.trim()

        if (!prompt) {
            toast.error('Please enter a task for the selected skills')
            return
        }

        if (selectedSkills.length === 0) {
            toast.error('Please select at least one skill')
            return
        }

        if (readySandboxes.length === 0) {
            toast.error('No available sandboxes. Please wait for one to become ready.')
            return
        }

        const reservedSandbox = readySandboxes[0]
        const conversationId = currentConversationId ?? await createConversation()
        setLocalSandboxExecution({
            sandboxIndex: reservedSandbox.sandboxIndex,
            prompt,
            startedAt: Date.now(),
            completedAt: null,
            skillNames: selectedSkills.map((skill) => skill.name),
        })
        setUserMessage('')

        try {
            await executeSkills(
                prompt,
                conversationId,
                selectedSkills.map((skill) => skill.id),
                attachedFiles.map((file) => file.id)
            )
            const latestRun = useAgentSkillsStore.getState().executionRunsByConversation[conversationId]?.at(-1)
            setSelectedRunId(latestRun?.id ?? null)
            setAttachedFiles([])
        } catch (error) {
            setUserMessage(prompt)
            toast.error(error instanceof Error ? error.message : 'Execution failed')
        }
    }

    return (
        <div className="flex h-full w-full flex-col gap-6 overflow-hidden bg-[linear-gradient(180deg,#f8fbff_0%,#eef4f8_100%)] p-4 lg:p-6 xl:flex-row">
            <Card className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-[0_20px_80px_rgba(15,23,42,0.08)]">
                <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3 sm:px-6">
                    <div className="space-y-0.5">
                        <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
                            <Sparkles className="h-3.5 w-3.5 text-sky-600" />
                            Agent Skills Workspace
                        </div>
                        <h1 className="text-base font-semibold text-slate-900">Chat and run selected skills</h1>
                    </div>
                    <div className="hidden items-center gap-2 sm:flex">
                        <Badge variant="outline" className="border-sky-200 bg-sky-50 text-xs text-sky-700">
                            {selectedSkills.length} selected skills
                        </Badge>
                        <Badge variant="outline" className="border-emerald-200 bg-emerald-50 text-xs text-emerald-700">
                            {readySandboxes.length} sandboxes ready
                        </Badge>
                    </div>
                </div>

                <div className="min-h-0 flex-1 overflow-hidden">
                    <ScrollArea className="h-full bg-white">
                        <div className="py-4 overflow-x-hidden">
                            {currentConversationRuns.length === 0 && (
                                <div className="flex min-h-[50vh] flex-col items-center justify-center px-6 text-center">
                                    <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-[22px] bg-tech-gradient shadow-[0_22px_50px_rgba(18,130,79,0.24)]">
                                        <Bot className="h-8 w-8 text-white" />
                                    </div>
                                    <h2 className="text-xl font-semibold text-text-primary">Start a new Agent Skills conversation</h2>
                                    <p className="mt-2 max-w-xl text-sm leading-6 text-text-muted">
                                        Pick skills on the right, upload support files, then send a task.
                                    </p>
                                </div>
                            )}

                            {currentConversationRuns.map((run) => (
                                <div
                                    key={run.id}
                                    id={`run-${run.id}`}
                                    className={`transition ${selectedRunId === run.id ? 'bg-primary/5' : ''}`}
                                >
                                    {/* User task — right-aligned */}
                                    <div className="flex w-full flex-row-reverse gap-3 p-4">
                                        <Avatar className="h-9 w-9 shrink-0 border">
                                            <AvatarFallback>
                                                <User className="h-4 w-4" />
                                            </AvatarFallback>
                                        </Avatar>
                                        <div className="flex min-w-0 max-w-[80%] flex-col items-end gap-1">
                                            <div className="rounded-xl bg-primary px-5 py-3 text-[15px] leading-relaxed text-white">
                                                <p className="whitespace-pre-wrap">{run.prompt}</p>
                                                {run.attachedFiles.length > 0 && (
                                                    <div className="mt-3 flex flex-wrap gap-2 border-t border-white/20 pt-3">
                                                        {run.attachedFiles.map((file) => (
                                                            <span
                                                                key={file.id}
                                                                className="inline-flex items-center gap-1.5 rounded-full bg-white/20 px-2.5 py-1 text-xs"
                                                            >
                                                                <FileText className="h-3 w-3" />
                                                                {file.name}
                                                            </span>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                            <span className="text-xs text-text-muted">{formatTimestamp(run.createdAt)}</span>
                                        </div>
                                    </div>

                                    {/* Skill execution — left-aligned */}
                                    <div className="flex w-full flex-row gap-3 p-4">
                                        <Avatar className="h-9 w-9 shrink-0">
                                            <AvatarFallback className="bg-primary text-white">
                                                <Bot className="h-4 w-4" />
                                            </AvatarFallback>
                                        </Avatar>
                                        <div className="min-w-0 flex-1 flex flex-col items-start gap-1.5">
                                            <div className="w-full rounded-xl border border-border bg-surface px-5 py-4 overflow-hidden">
                                                {/* Header */}
                                                <div className="mb-3 flex items-start justify-between gap-4">
                                                    <span className="text-sm text-text-muted">
                                                        {run.usedSkills.map((skill) => skill.name).join(', ') || 'SANDBOX'}
                                                    </span>
                                                    <Badge
                                                        variant="outline"
                                                        className={`shrink-0 text-xs font-medium ${
                                                            run.status === 'error'
                                                                ? 'border-red-200 bg-red-50 text-red-700'
                                                                : run.status === 'running'
                                                                    ? 'border-amber-200 bg-amber-50 text-amber-700'
                                                                    : 'border-emerald-200 bg-emerald-50 text-emerald-700'
                                                        }`}
                                                    >
                                                        {getRunStatusLabel(run.status)}
                                                    </Badge>
                                                </div>

                                                {/* While running: show spinner + live status */}
                                                {run.status === 'running' && (
                                                    <div className="flex flex-col gap-2 py-2">
                                                        <div className="flex items-center gap-3 text-sm text-text-primary">
                                                            <Loader2 className="h-4 w-4 shrink-0 animate-spin text-primary" />
                                                            <span className="line-clamp-2 text-text-muted">
                                                                {run.liveStatus || 'Preparing sandbox...'}
                                                            </span>
                                                        </div>
                                                    </div>
                                                )}

                                                {/* After done: show success/error message only */}
                                                {run.status !== 'running' && (
                                                    <div className={`text-sm ${run.status === 'error' ? 'text-red-600' : 'text-emerald-600'}`}>
                                                        {run.status === 'error'
                                                            ? (run.error || 'Execution failed.')
                                                            : 'Execution completed successfully.'}
                                                    </div>
                                                )}

                                                {/* Output files */}
                                                {run.outputFiles && run.outputFiles.length > 0 && (
                                                    <div className="mt-3 space-y-2">
                                                        {run.outputFiles.map((file, index) => {
                                                            const fileUrl = file.blob_url
                                                                || (
                                                                    file.download_url?.startsWith('http')
                                                                        ? file.download_url
                                                                        : `${API_BASE_URL}${file.download_url}`
                                                                )
                                                            return (
                                                                <div
                                                                    key={`${file.name}-${index}`}
                                                                    className="flex items-center gap-3 rounded-xl border border-border bg-white px-4 py-3"
                                                                >
                                                                    <FileText className="h-5 w-5 shrink-0 text-primary" />
                                                                    <div className="min-w-0 flex-1">
                                                                        <p className="truncate text-sm font-medium text-text-primary">{file.name}</p>
                                                                        <p className="text-xs text-text-muted">{(file.size / 1024).toFixed(1)} KB</p>
                                                                    </div>
                                                                    <div className="flex shrink-0 items-center gap-2">
                                                                        <a
                                                                            href={fileUrl}
                                                                            download={file.name}
                                                                            className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-white px-3 text-xs font-medium text-text-primary transition hover:bg-surface"
                                                                        >
                                                                            <Download className="h-3.5 w-3.5" />
                                                                            Download
                                                                        </a>
                                                                        <button
                                                                            type="button"
                                                                            onClick={() => setViewingFile({ url: fileUrl, filename: file.name })}
                                                                            className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-medium text-white transition hover:bg-primary/90"
                                                                        >
                                                                            <Eye className="h-3.5 w-3.5" />
                                                                            Preview
                                                                        </button>
                                                                    </div>
                                                                </div>
                                                            )
                                                        })}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                            <div ref={chatScrollRef} />
                        </div>
                    </ScrollArea>
                </div>

                <div className="border-t border-border bg-white p-4">
                    {attachedFiles.length > 0 && (
                        <div className="mb-3 flex flex-wrap gap-2">
                            {attachedFiles.map((file) => (
                                <div
                                    key={file.id}
                                    className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1.5 text-xs text-text-primary"
                                >
                                    <FileText className="h-3.5 w-3.5 text-primary" />
                                    <span className="max-w-[180px] truncate">{file.name}</span>
                                    <span className="text-text-muted">{file.ingestionStatus}</span>
                                    <button
                                        type="button"
                                        onClick={() => handleRemoveAttachedFile(file.id)}
                                        className="rounded-full text-text-muted transition hover:text-text-primary"
                                        aria-label={`Remove ${file.name}`}
                                    >
                                        <X className="h-3.5 w-3.5" />
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}

                    <div className="rounded-xl border border-border bg-surface p-3 transition focus-within:border-primary focus-within:bg-white">
                        <Textarea
                            value={userMessage}
                            onChange={(event) => setUserMessage(event.target.value)}
                            placeholder="Describe the task you want the selected skills to execute..."
                            disabled={isExecuting}
                            className="min-h-[40px] max-h-[120px] resize-none border-0 bg-transparent px-2 py-1.5 text-sm text-text-primary placeholder:text-text-muted focus-visible:ring-0 focus-visible:ring-offset-0"
                            onKeyDown={(event) => {
                                if (event.key === 'Enter' && !event.shiftKey) {
                                    event.preventDefault()
                                    void handleExecute()
                                }
                            }}
                            onInput={(event) => {
                                const target = event.target as HTMLTextAreaElement
                                target.style.height = 'auto'
                                target.style.height = `${target.scrollHeight}px`
                            }}
                        />

                        <div className="mt-3 flex flex-col gap-3 border-t border-border pt-3 sm:flex-row sm:items-center sm:justify-between">
                            <div className="flex flex-wrap items-center gap-2 text-xs text-text-muted">
                                <input
                                    ref={chatUploadInputRef}
                                    type="file"
                                    multiple
                                    className="hidden"
                                    id="agent-skills-chat-upload"
                                    onChange={handleChatFileUpload}
                                />
                                <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    className="h-9 rounded-lg px-3 text-text-primary hover:bg-primary/10 hover:text-primary"
                                    onClick={() => chatUploadInputRef.current?.click()}
                                    disabled={isUploadingChatFile}
                                >
                                    {isUploadingChatFile ? (
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    ) : (
                                        <Paperclip className="mr-2 h-4 w-4" />
                                    )}
                                    Upload file
                                </Button>
                                <span>{selectedSkills.length} skills selected</span>
                                <span className="hidden text-border sm:inline">|</span>
                                <span>{readySandboxes.length}/10 sandboxes ready</span>
                            </div>

                            <Button
                                type="button"
                                onClick={() => void handleExecute()}
                                disabled={isExecuting || !userMessage.trim()}
                                className="h-10 rounded-lg bg-primary px-5 text-white hover:bg-primary/90"
                            >
                                {isExecuting ? (
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                ) : (
                                    <Play className="mr-2 h-4 w-4" />
                                )}
                                Run skills
                            </Button>
                        </div>
                    </div>
                </div>
            </Card>

            <Card className="flex min-h-0 w-full flex-col overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-[0_20px_80px_rgba(15,23,42,0.08)] xl:w-[28rem] xl:min-w-[28rem]">
                <div className="border-b border-slate-200 px-5 py-3 sm:px-6">
                    <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
                        <Boxes className="h-3.5 w-3.5 text-sky-600" />
                        Workspace Panels
                    </div>
                    <h2 className="mt-0.5 text-base font-semibold text-slate-900">Skills and sandbox activity</h2>
                </div>

                <Tabs defaultValue="skills" className="flex min-h-0 flex-1 flex-col">
                    <div className="border-b border-slate-200 px-5 py-4 sm:px-6">
                        <TabsList className="grid w-full grid-cols-2 rounded-2xl bg-slate-100 p-1">
                            <TabsTrigger value="skills" className="rounded-xl data-[state=active]:bg-white">
                                Skills
                            </TabsTrigger>
                            <TabsTrigger value="sandbox" className="rounded-xl data-[state=active]:bg-white">
                                Sandbox
                            </TabsTrigger>
                        </TabsList>
                    </div>

                    <TabsContent value="skills" className="mt-0 min-h-0 flex-1 px-3 py-3 sm:px-4">
                        <ScrollArea className="h-full">
                            <div className="space-y-4 pb-4">
                                <label
                                    htmlFor="agent-skill-upload"
                                    onDragOver={(event) => {
                                        event.preventDefault()
                                        setIsSkillDragActive(true)
                                    }}
                                    onDragLeave={() => setIsSkillDragActive(false)}
                                    onDrop={(event) => void handleSkillDrop(event)}
                                    className={`block cursor-pointer rounded-[24px] border-2 border-dashed px-6 py-8 text-center transition ${
                                        isSkillDragActive
                                            ? 'border-sky-400 bg-sky-50'
                                            : 'border-slate-200 bg-slate-50 hover:border-sky-300 hover:bg-sky-50/60'
                                    }`}
                                >
                                    <input
                                        ref={skillUploadInputRef}
                                        id="agent-skill-upload"
                                        type="file"
                                        accept=".md,.zip"
                                        className="hidden"
                                        onChange={handleSkillFileInputChange}
                                    />
                                    <input
                                        ref={skillFolderInputRef}
                                        id="agent-skill-folder-upload"
                                        type="file"
                                        className="hidden"
                                        {...({ webkitdirectory: '', directory: '' } as React.InputHTMLAttributes<HTMLInputElement>)}
                                        onChange={(event) => void handleSkillFolderInputChange(event)}
                                    />
                                    {isZippingFolder ? (
                                        <>
                                            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-white shadow-sm">
                                                <Loader2 className="h-6 w-6 animate-spin text-sky-600" />
                                            </div>
                                            <h3 className="mt-4 text-lg font-semibold text-slate-900">Packaging folder...</h3>
                                            <p className="mt-2 text-sm leading-6 text-slate-500">Reading files and creating archive</p>
                                        </>
                                    ) : (
                                        <>
                                            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-white shadow-sm">
                                                <Upload className="h-6 w-6 text-sky-600" />
                                            </div>
                                            <h3 className="mt-4 text-lg font-semibold text-slate-900">Upload skill files or folders</h3>
                                            <p className="mt-2 text-sm leading-6 text-slate-500">
                                                Drag and drop files, folders, or click to browse. Supports SKILL.md, .zip, and skill folders.
                                            </p>
                                            <button
                                                type="button"
                                                className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm transition hover:bg-slate-50"
                                                onClick={(event) => {
                                                    event.preventDefault()
                                                    event.stopPropagation()
                                                    skillFolderInputRef.current?.click()
                                                }}
                                            >
                                                <FolderOpen className="h-3.5 w-3.5" />
                                                Upload folder
                                            </button>
                                        </>
                                    )}
                                </label>

                                {pendingSkillUpload && (
                                    <Card className="rounded-[24px] border-sky-200 bg-sky-50 p-4">
                                        <div className="flex items-start justify-between gap-3">
                                            <div className="min-w-0">
                                                <div className="text-sm font-semibold text-slate-900">Ready to upload</div>
                                                <p className="mt-1 truncate text-sm text-slate-600">{pendingSkillUpload.name}</p>
                                                <p className="mt-1 text-xs text-slate-500">{formatFileSize(pendingSkillUpload.size)}</p>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <Button
                                                    type="button"
                                                    variant="outline"
                                                    size="sm"
                                                    className="rounded-xl"
                                                    onClick={() => setPendingSkillUpload(null)}
                                                    disabled={isUploadingSkill}
                                                >
                                                    Clear
                                                </Button>
                                                <Button
                                                    type="button"
                                                    size="sm"
                                                    className="rounded-xl bg-slate-900 text-white hover:bg-slate-800"
                                                    onClick={() => void handleSkillUploadConfirm()}
                                                    disabled={isUploadingSkill}
                                                >
                                                    {isUploadingSkill ? (
                                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                                    ) : (
                                                        <Upload className="mr-2 h-4 w-4" />
                                                    )}
                                                    Upload
                                                </Button>
                                            </div>
                                        </div>
                                    </Card>
                                )}

                                <div className="flex items-center justify-between px-1">
                                    <div>
                                        <div className="text-sm font-semibold text-slate-900">Uploaded skills</div>
                                        <div className="text-xs text-slate-500">Skills appear below as they are added</div>
                                    </div>
                                    <Badge variant="outline" className="border-slate-200 bg-slate-50 text-slate-600">
                                        {skills.length} total
                                    </Badge>
                                </div>

                                <div className="space-y-3">
                                    {isLoading ? (
                                        <Card className="rounded-[24px] border-dashed p-8 text-center text-slate-500">
                                            <Loader2 className="mx-auto mb-3 h-6 w-6 animate-spin" />
                                            Loading skills...
                                        </Card>
                                    ) : sortedSkills.length === 0 ? (
                                        <Card className="rounded-[24px] border-dashed p-8 text-center text-slate-500">
                                            <Bot className="mx-auto mb-3 h-10 w-10 text-slate-300" />
                                            No skills uploaded yet.
                                        </Card>
                                    ) : (
                                        sortedSkills.map((skill) => (
                                            <Card
                                                key={skill.id}
                                                className={`rounded-[24px] p-4 transition ${skill.isSelected ? 'border-sky-200 bg-sky-50/80' : 'border-slate-200 bg-white'}`}
                                            >
                                                <div className="flex items-start gap-3">
                                                    <Checkbox
                                                        checked={skill.isSelected}
                                                        onCheckedChange={(checked) => void handleSkillSelection(skill.id, Boolean(checked))}
                                                        className="mt-1"
                                                    />
                                                    <div className="min-w-0 flex-1">
                                                        <div className="flex flex-wrap items-center gap-2">
                                                            <div className="truncate text-sm font-semibold text-slate-900">{skill.name}</div>
                                                            <Badge variant="outline" className="border-slate-200 bg-white text-slate-600">
                                                                {skill.fileType.toUpperCase()}
                                                            </Badge>
                                                            {skill.isSelected && (
                                                                <Badge variant="outline" className="border-sky-200 bg-sky-100 text-sky-700">
                                                                    Selected
                                                                </Badge>
                                                            )}
                                                        </div>
                                                        {skill.description && (
                                                            <p className="mt-2 text-sm leading-6 text-slate-600">{skill.description}</p>
                                                        )}
                                                        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                                                            <span>{formatFileSize(skill.size)}</span>
                                                            <span className="text-slate-300">|</span>
                                                            <span>{formatTimestamp(skill.createdAt)}</span>
                                                            {skill.allowedTools && (
                                                                <>
                                                                    <span className="text-slate-300">|</span>
                                                                    <span className="truncate">Tools: {skill.allowedTools}</span>
                                                                </>
                                                            )}
                                                        </div>
                                                    </div>
                                                    <Button
                                                        type="button"
                                                        variant="ghost"
                                                        size="icon"
                                                        className="h-9 w-9 rounded-xl text-slate-400 hover:bg-red-50 hover:text-red-600"
                                                        onClick={() => void handleDeleteSkill(skill.id)}
                                                    >
                                                        <Trash2 className="h-4 w-4" />
                                                    </Button>
                                                </div>
                                            </Card>
                                        ))
                                    )}
                                </div>
                            </div>
                        </ScrollArea>
                    </TabsContent>

                    <TabsContent value="sandbox" className="mt-0 min-h-0 flex-1 px-3 py-3 sm:px-4">
                        <ScrollArea className="h-full">
                            <div className="space-y-5 pb-4">
                                <div className="flex items-start justify-between gap-3 px-1">
                                    <div>
                                        <div className="text-sm font-semibold text-slate-900">Sandbox activity</div>
                                        <div className="text-xs text-slate-500">Monitor running sandboxes.</div>
                                    </div>
                                    <Button
                                        type="button"
                                        variant="ghost"
                                        size="icon"
                                        className="h-9 w-9 rounded-xl"
                                        onClick={() => void fetchSandboxes()}
                                    >
                                        <RefreshCw className="h-4 w-4" />
                                    </Button>
                                </div>

                                <div className="flex flex-wrap gap-2 px-1">
                                    <Badge variant="outline" className="rounded-full border-emerald-200 bg-emerald-50 px-3 py-1 text-emerald-700">
                                        {displaySandboxes.filter((sandbox) => sandbox.status === 'ready').length} ready
                                    </Badge>
                                    <Badge variant="outline" className="rounded-full border-amber-200 bg-amber-50 px-3 py-1 text-amber-700">
                                        {displaySandboxes.filter((sandbox) => sandbox.status === 'busy').length} busy
                                    </Badge>
                                    <Badge variant="outline" className="rounded-full border-red-200 bg-red-50 px-3 py-1 text-red-700">
                                        {displaySandboxes.filter((sandbox) => sandbox.status === 'error').length} error
                                    </Badge>
                                </div>

                                <div className="space-y-2 px-1">
                                    {displaySandboxes.map((sandbox) => {
                                        const sandboxSkillNames = localSandboxExecution && sandbox.sandboxIndex === localSandboxExecution.sandboxIndex
                                            ? localSandboxExecution.skillNames
                                            : sandbox.currentSkillId && skillMap.get(sandbox.currentSkillId)
                                                ? [skillMap.get(sandbox.currentSkillId)?.name || '']
                                                : []

                                        return (
                                        <div
                                            key={sandbox.id}
                                            className="rounded-[22px] border border-slate-200 bg-white px-4 py-3 transition hover:border-slate-300"
                                        >
                                            <div className="flex items-start justify-between gap-3">
                                                <div className="min-w-0 flex-1">
                                                    <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                                                        {getSandboxStatusIcon(sandbox.status)}
                                                        <span>Sandbox #{sandbox.sandboxIndex + 1}</span>
                                                    </div>
                                                    <div className="mt-1 truncate text-xs text-slate-500">
                                                        {sandboxSkillNames.length > 0
                                                            ? `Skills in this run: ${sandboxSkillNames.length}`
                                                            : 'No skill running'}
                                                    </div>
                                                    {sandboxSkillNames.length > 0 && (
                                                        <div className="mt-2 flex flex-wrap gap-2">
                                                            {sandboxSkillNames.map((skillName) => (
                                                                <span
                                                                    key={`${sandbox.id}-${skillName}`}
                                                                    className="inline-flex items-center rounded-xl border border-sky-200 bg-sky-50 px-3 py-1.5 text-xs font-medium text-sky-700"
                                                                >
                                                                    {skillName}
                                                                </span>
                                                            ))}
                                                        </div>
                                                    )}
                                                    {sandbox.taskDescription && (
                                                        <p className="mt-2 line-clamp-2 text-sm text-slate-600">{sandbox.taskDescription}</p>
                                                    )}
                                                </div>
                                                <Badge
                                                    variant="outline"
                                                    className={sandbox.status === 'error'
                                                        ? 'rounded-full border-red-200 bg-red-50 text-red-700'
                                                        : sandbox.status === 'busy'
                                                            ? 'rounded-full border-amber-200 bg-amber-50 text-amber-700'
                                                            : 'rounded-full border-emerald-200 bg-emerald-50 text-emerald-700'}
                                                >
                                                    {sandbox.status}
                                                </Badge>
                                            </div>

                                            <div className="mt-3 flex items-center gap-3">
                                                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100">
                                                    <div
                                                        className={`h-full rounded-full transition-all ${sandbox.status === 'error' ? 'bg-red-500' : sandbox.status === 'busy' ? 'bg-amber-500' : 'bg-emerald-500'}`}
                                                        style={{ width: `${sandbox.progress}%` }}
                                                    />
                                                </div>
                                                <span className="w-10 shrink-0 text-right text-xs font-medium text-slate-500">
                                                    {sandbox.progress}%
                                                </span>
                                            </div>

                                            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-slate-500">
                                                <span>Started: {formatTimestamp(sandbox.startedAt)}</span>
                                                <span>Completed: {formatTimestamp(sandbox.completedAt)}</span>
                                            </div>
                                        </div>
                                        )
                                    })}
                                </div>


                            </div>
                        </ScrollArea>
                    </TabsContent>
                </Tabs>
            </Card>

            {viewingFile && (
                <FileViewer
                    isOpen={!!viewingFile}
                    onClose={() => setViewingFile(null)}
                    fileUrl={viewingFile.url}
                    filename={viewingFile.filename}
                />
            )}
        </div>
    )
}
