import { AlertCircle, CheckCircle2, Clapperboard, Loader2 } from 'lucide-react'

import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import { useVideoStore } from '@/store/video-store'

export function VideoPreviewPanel() {
    const currentJob = useVideoStore((state) => state.currentJob)
    const storyboard = useVideoStore((state) => state.storyboard)
    const statusSteps = useVideoStore((state) => state.statusSteps)
    const isGenerating = useVideoStore((state) => state.isGenerating)
    const error = useVideoStore((state) => state.error)
    const activeStatus = statusSteps[statusSteps.length - 1]

    return (
        <section className="flex h-full min-w-0 flex-1 flex-col bg-[linear-gradient(180deg,#fbfdf9_0%,#eef7f1_100%)]">
            <div className="flex items-center justify-between border-b border-border/80 bg-white/80 px-5 py-4">
                <div>
                    <h2 className="font-display text-lg font-bold text-text-primary">
                        Preview
                    </h2>
                    <p className="text-sm text-text-muted">
                        {currentJob
                            ? `${currentJob.durationSeconds}s at ${currentJob.fps} FPS`
                            : 'No video rendered yet'}
                    </p>
                </div>
                <div
                    className={cn(
                        'flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold',
                        error
                            ? 'bg-red-50 text-red-700'
                            : currentJob?.videoUrl
                                ? 'bg-emerald-50 text-emerald-700'
                                : 'bg-surface text-text-muted'
                    )}
                >
                    {error ? (
                        <AlertCircle className="h-4 w-4" />
                    ) : currentJob?.videoUrl ? (
                        <CheckCircle2 className="h-4 w-4" />
                    ) : isGenerating ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                        <Clapperboard className="h-4 w-4" />
                    )}
                    {error ? 'Failed' : currentJob?.videoUrl ? 'Ready' : isGenerating ? 'Rendering' : 'Idle'}
                </div>
            </div>

            <div className="grid min-h-0 flex-1 grid-rows-[minmax(0,1fr)_260px] gap-4 p-5">
                <div className="flex min-h-0 items-center justify-center overflow-hidden rounded-xl border border-border bg-[#0b1110] shadow-sm">
                    {currentJob?.videoUrl ? (
                        <video
                            key={currentJob.videoUrl}
                            src={currentJob.videoUrl}
                            poster={currentJob.thumbnailUrl || undefined}
                            controls
                            className={cn(
                                'max-h-full max-w-full bg-black',
                                currentJob.aspectRatio === '9:16'
                                    ? 'aspect-[9/16]'
                                    : currentJob.aspectRatio === '1:1'
                                        ? 'aspect-square'
                                        : 'aspect-video'
                            )}
                        />
                    ) : (
                        <div className="flex flex-col items-center gap-3 px-6 text-center text-white/75">
                            {isGenerating ? (
                                <Loader2 className="h-8 w-8 animate-spin" />
                            ) : (
                                <Clapperboard className="h-8 w-8" />
                            )}
                            <span className="text-sm font-medium">
                                {activeStatus || 'Video output will appear here'}
                            </span>
                        </div>
                    )}
                </div>

                <div className="grid min-h-0 grid-cols-2 gap-4">
                    <div className="min-h-0 rounded-xl border border-border bg-white shadow-sm">
                        <div className="border-b border-border px-4 py-3 text-sm font-semibold text-text-primary">
                            Progress
                        </div>
                        <ScrollArea className="h-[210px]">
                            <div className="space-y-2 p-4">
                                {error && (
                                    <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
                                        {error}
                                    </div>
                                )}
                                {statusSteps.length === 0 && !error ? (
                                    <div className="text-sm text-text-muted">Waiting for render</div>
                                ) : (
                                    statusSteps.map((step, index) => (
                                        <div
                                            key={`${step}-${index}`}
                                            className="flex items-center gap-2 rounded-lg bg-surface px-3 py-2 text-sm text-text-primary"
                                        >
                                            {index === statusSteps.length - 1 && isGenerating ? (
                                                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                                            ) : (
                                                <CheckCircle2 className="h-4 w-4 text-primary" />
                                            )}
                                            <span>{step}</span>
                                        </div>
                                    ))
                                )}
                            </div>
                        </ScrollArea>
                    </div>

                    <div className="min-h-0 rounded-xl border border-border bg-white shadow-sm">
                        <div className="border-b border-border px-4 py-3 text-sm font-semibold text-text-primary">
                            Storyboard
                        </div>
                        <ScrollArea className="h-[210px]">
                            <div className="space-y-2 p-4">
                                {storyboard.length === 0 ? (
                                    <div className="text-sm text-text-muted">No scenes yet</div>
                                ) : (
                                    storyboard.map((scene) => (
                                        <div key={scene.index} className="rounded-lg border border-border px-3 py-2">
                                            <div className="flex items-center justify-between gap-2">
                                                <span className="text-sm font-semibold text-text-primary">
                                                    {scene.title}
                                                </span>
                                                <span className="text-xs text-text-muted">
                                                    {scene.duration_seconds}s
                                                </span>
                                            </div>
                                            <p className="mt-1 line-clamp-2 text-xs text-text-muted">
                                                {scene.on_screen_text || scene.narration}
                                            </p>
                                        </div>
                                    ))
                                )}
                            </div>
                        </ScrollArea>
                    </div>
                </div>
            </div>
        </section>
    )
}
