import { Check, Edit2, Film, Loader2, Play, Search, Trash2, X } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { type VideoAspectRatio, type VideoStyle, useVideoStore } from '@/store/video-store'

const styles: Array<{ value: VideoStyle; label: string }> = [
    { value: 'educational', label: 'Educational' },
    { value: 'cinematic', label: 'Cinematic' },
    { value: 'product_demo', label: 'Product demo' },
    { value: 'social_short', label: 'Social short' },
    { value: 'slideshow', label: 'Slideshow' },
]

const ratios: Array<{ value: VideoAspectRatio; label: string }> = [
    { value: '16:9', label: '16:9 Landscape' },
    { value: '9:16', label: '9:16 Vertical' },
    { value: '1:1', label: '1:1 Square' },
]

export function VideoSettingsPanel() {
    const form = useVideoStore((state) => state.form)
    const jobs = useVideoStore((state) => state.jobs)
    const currentJob = useVideoStore((state) => state.currentJob)
    const setForm = useVideoStore((state) => state.setForm)
    const loadJob = useVideoStore((state) => state.loadJob)
    const renameJob = useVideoStore((state) => state.renameJob)
    const deleteJob = useVideoStore((state) => state.deleteJob)
    const generateVideo = useVideoStore((state) => state.generateVideo)
    const isGenerating = useVideoStore((state) => state.isGenerating)
    const [editingJobId, setEditingJobId] = useState<number | null>(null)
    const [editingTitle, setEditingTitle] = useState('')

    const canGenerate = form.prompt.trim().length > 0 && !isGenerating
    const startRename = (jobId: number, title: string) => {
        setEditingJobId(jobId)
        setEditingTitle(title)
    }
    const cancelRename = () => {
        setEditingJobId(null)
        setEditingTitle('')
    }
    const confirmRename = async () => {
        if (!editingJobId || !editingTitle.trim()) return
        await renameJob(editingJobId, editingTitle)
        cancelRename()
    }

    return (
        <section className="flex h-full min-h-0 flex-col border-r border-border/80 bg-white">
            <div className="border-b border-border/80 px-5 py-4">
                <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                        <Film className="h-5 w-5" />
                    </div>
                    <div>
                        <h1 className="font-display text-xl font-bold text-text-primary">
                            Video Studio
                        </h1>
                        <p className="text-sm text-text-muted">Remotion render workflow</p>
                    </div>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto px-5 py-5">
                <div className="space-y-5">
                    <div className="space-y-2">
                        <Label htmlFor="video-prompt">Prompt</Label>
                        <Textarea
                            id="video-prompt"
                            value={form.prompt}
                            onChange={(event) => setForm({ prompt: event.target.value })}
                            disabled={isGenerating}
                            placeholder="Create a concise explainer video about multi-agent AI workflows..."
                            className="min-h-[160px] resize-none rounded-xl"
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-2">
                            <Label htmlFor="duration">Duration</Label>
                            <div className="rounded-xl border border-border bg-surface px-3 py-3">
                                <div className="flex items-center justify-between">
                                    <span className="text-sm font-semibold text-text-primary">
                                        {form.durationSeconds}s
                                    </span>
                                    <span className="text-xs text-text-muted">Max 30s</span>
                                </div>
                                <input
                                    id="duration"
                                    type="range"
                                    min={5}
                                    max={30}
                                    step={1}
                                    value={form.durationSeconds}
                                    disabled={isGenerating}
                                    onChange={(event) =>
                                        setForm({ durationSeconds: Number(event.target.value) })
                                    }
                                    className="mt-3 w-full accent-primary"
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label>FPS</Label>
                            <Select
                                value={String(form.fps)}
                                disabled={isGenerating}
                                onValueChange={(value) => setForm({ fps: Number(value) as 24 | 30 })}
                            >
                                <SelectTrigger className="rounded-xl">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="24">24 FPS</SelectItem>
                                    <SelectItem value="30">30 FPS</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-2">
                            <Label>Aspect ratio</Label>
                            <Select
                                value={form.aspectRatio}
                                disabled={isGenerating}
                                onValueChange={(value) =>
                                    setForm({ aspectRatio: value as VideoAspectRatio })
                                }
                            >
                                <SelectTrigger className="rounded-xl">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {ratios.map((ratio) => (
                                        <SelectItem key={ratio.value} value={ratio.value}>
                                            {ratio.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <Label>Style</Label>
                            <Select
                                value={form.style}
                                disabled={isGenerating}
                                onValueChange={(value) => setForm({ style: value as VideoStyle })}
                            >
                                <SelectTrigger className="rounded-xl">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {styles.map((style) => (
                                        <SelectItem key={style.value} value={style.value}>
                                            {style.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <label
                        className={cn(
                            'flex cursor-pointer items-center gap-3 rounded-xl border border-border bg-surface px-3 py-3',
                            isGenerating && 'cursor-not-allowed opacity-70'
                        )}
                    >
                        <Checkbox
                            checked={form.webSearchEnabled}
                            disabled={isGenerating}
                            onCheckedChange={(checked) =>
                                setForm({ webSearchEnabled: checked === true })
                            }
                        />
                        <span className="flex min-w-0 items-center gap-2 text-sm font-medium text-text-primary">
                            <Search className="h-4 w-4 text-primary" />
                            Web search
                        </span>
                    </label>

                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <Label>Recent videos</Label>
                            <span className="text-xs text-text-muted">{jobs.length} total</span>
                        </div>
                        <div className="max-h-56 space-y-2 overflow-y-auto rounded-xl border border-border bg-white p-2">
                            {jobs.length === 0 ? (
                                <div className="px-2 py-3 text-sm text-text-muted">
                                    No videos generated yet
                                </div>
                            ) : (
                                jobs.slice(0, 8).map((job) => (
                                    <div
                                        key={job.id}
                                        className={cn(
                                            'grid grid-cols-[1fr_auto] items-center gap-1 rounded-lg px-2 py-2 transition hover:bg-surface',
                                            currentJob?.id === job.id && 'bg-primary/10 text-primary'
                                        )}
                                    >
                                        {editingJobId === job.id ? (
                                            <div className="min-w-0">
                                                <Input
                                                    value={editingTitle}
                                                    disabled={isGenerating}
                                                    onChange={(event) => setEditingTitle(event.target.value)}
                                                    onKeyDown={(event) => {
                                                        if (event.key === 'Enter') {
                                                            void confirmRename()
                                                        }
                                                        if (event.key === 'Escape') {
                                                            cancelRename()
                                                        }
                                                    }}
                                                    className="h-8 rounded-lg"
                                                    autoFocus
                                                />
                                            </div>
                                        ) : (
                                            <button
                                                type="button"
                                                disabled={isGenerating}
                                                onClick={() => void loadJob(job.id)}
                                                className="min-w-0 text-left"
                                            >
                                                <div className="flex items-center justify-between gap-2">
                                                    <span className="truncate text-sm font-semibold">
                                                        {job.title}
                                                    </span>
                                                    <span className="shrink-0 text-xs text-text-muted">
                                                        {job.durationSeconds}s
                                                    </span>
                                                </div>
                                                <div className="mt-1 flex items-center justify-between gap-2 text-xs text-text-muted">
                                                    <span>{job.status}</span>
                                                    <span>{job.aspectRatio}</span>
                                                </div>
                                            </button>
                                        )}

                                        <div className="flex shrink-0 items-center gap-1">
                                            {editingJobId === job.id ? (
                                                <>
                                                    <Button
                                                        type="button"
                                                        variant="ghost"
                                                        size="icon"
                                                        disabled={isGenerating || !editingTitle.trim()}
                                                        onClick={() => void confirmRename()}
                                                        className="h-7 w-7 rounded-md text-primary hover:bg-primary/10"
                                                    >
                                                        <Check className="h-3.5 w-3.5" />
                                                    </Button>
                                                    <Button
                                                        type="button"
                                                        variant="ghost"
                                                        size="icon"
                                                        disabled={isGenerating}
                                                        onClick={cancelRename}
                                                        className="h-7 w-7 rounded-md text-text-muted hover:bg-surface"
                                                    >
                                                        <X className="h-3.5 w-3.5" />
                                                    </Button>
                                                </>
                                            ) : (
                                                <>
                                                    <Button
                                                        type="button"
                                                        variant="ghost"
                                                        size="icon"
                                                        disabled={isGenerating}
                                                        onClick={() => startRename(job.id, job.title)}
                                                        className="h-7 w-7 rounded-md text-text-muted hover:bg-primary/10 hover:text-primary"
                                                    >
                                                        <Edit2 className="h-3.5 w-3.5" />
                                                    </Button>
                                                    <Button
                                                        type="button"
                                                        variant="ghost"
                                                        size="icon"
                                                        disabled={isGenerating}
                                                        onClick={() => void deleteJob(job.id)}
                                                        className="h-7 w-7 rounded-md text-text-muted hover:bg-red-50 hover:text-red-600"
                                                    >
                                                        <Trash2 className="h-3.5 w-3.5" />
                                                    </Button>
                                                </>
                                            )}
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </div>
            </div>

            <div className="border-t border-border/80 p-5">
                <Button
                    onClick={() => void generateVideo()}
                    disabled={!canGenerate}
                    className="h-11 w-full rounded-xl bg-primary text-white hover:bg-primary-hover"
                >
                    {isGenerating ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                        <Play className="mr-2 h-4 w-4" />
                    )}
                    Generate Video
                </Button>
            </div>
        </section>
    )
}
