import { create } from 'zustand'
import { apiFetch, apiFetchStream, type StreamEvent } from '@/lib/api'

export type VideoAspectRatio = '16:9' | '9:16' | '1:1'
export type VideoStyle =
    | 'cinematic'
    | 'educational'
    | 'product_demo'
    | 'social_short'
    | 'slideshow'

export type VideoScene = {
    index: number
    title: string
    narration: string
    visual_prompt: string
    on_screen_text: string
    duration_seconds: number
    image_url?: string | null
}

export type VideoGenerationJob = {
    id: number
    title: string
    prompt: string
    style: VideoStyle
    aspectRatio: VideoAspectRatio
    durationSeconds: number
    fps: 24 | 30
    webSearchEnabled: boolean
    status: string
    progress: number
    storyboard: { scenes: VideoScene[] } | null
    sources: Array<{ title: string; url: string; snippet: string }> | null
    videoUrl: string | null
    thumbnailUrl: string | null
    errorMessage: string | null
    createdAt: number
    updatedAt: number
    completedAt: number | null
}

type VideoGenerationApiResponse = {
    id: number
    title: string
    prompt: string
    style: VideoStyle
    aspect_ratio: VideoAspectRatio
    duration_seconds: number
    fps: 24 | 30
    web_search_enabled: boolean
    status: string
    progress: number
    storyboard?: { scenes: VideoScene[] } | null
    sources?: Array<{ title: string; url: string; snippet: string }> | null
    video_url?: string | null
    thumbnail_url?: string | null
    error_message?: string | null
    created_at: string
    updated_at: string
    completed_at?: string | null
}

export type VideoFormState = {
    prompt: string
    durationSeconds: number
    fps: 24 | 30
    aspectRatio: VideoAspectRatio
    style: VideoStyle
    webSearchEnabled: boolean
}

type VideoStore = {
    form: VideoFormState
    jobs: VideoGenerationJob[]
    currentJob: VideoGenerationJob | null
    storyboard: VideoScene[]
    statusSteps: string[]
    isGenerating: boolean
    error: string | null
    setForm: (patch: Partial<VideoFormState>) => void
    resetResult: () => void
    fetchJobs: () => Promise<void>
    loadJob: (jobId: number) => Promise<void>
    renameJob: (jobId: number, title: string) => Promise<void>
    deleteJob: (jobId: number) => Promise<void>
    generateVideo: () => Promise<void>
}

const defaultForm: VideoFormState = {
    prompt: '',
    durationSeconds: 15,
    fps: 30,
    aspectRatio: '16:9',
    style: 'educational',
    webSearchEnabled: true,
}

const mapJob = (job: VideoGenerationApiResponse): VideoGenerationJob => ({
    id: job.id,
    title: job.title || job.prompt,
    prompt: job.prompt,
    style: job.style,
    aspectRatio: job.aspect_ratio,
    durationSeconds: job.duration_seconds,
    fps: job.fps,
    webSearchEnabled: job.web_search_enabled,
    status: job.status,
    progress: job.progress,
    storyboard: job.storyboard || null,
    sources: job.sources || null,
    videoUrl: job.video_url || null,
    thumbnailUrl: job.thumbnail_url || null,
    errorMessage: job.error_message || null,
    createdAt: new Date(job.created_at).getTime(),
    updatedAt: new Date(job.updated_at).getTime(),
    completedAt: job.completed_at ? new Date(job.completed_at).getTime() : null,
})

const clampDuration = (duration: number) => Math.min(30, Math.max(5, duration))

export const useVideoStore = create<VideoStore>((set, get) => ({
    form: defaultForm,
    jobs: [],
    currentJob: null,
    storyboard: [],
    statusSteps: [],
    isGenerating: false,
    error: null,

    setForm: (patch) =>
        set((state) => ({
            form: {
                ...state.form,
                ...patch,
                durationSeconds:
                    patch.durationSeconds !== undefined
                        ? clampDuration(patch.durationSeconds)
                        : state.form.durationSeconds,
            },
        })),

    resetResult: () =>
        set({
            currentJob: null,
            storyboard: [],
            statusSteps: [],
            error: null,
        }),

    fetchJobs: async () => {
        const response = await apiFetch<VideoGenerationApiResponse[]>('/video-generations')
        const jobs = response.map(mapJob)
        set((state) => {
            const currentJob = state.currentJob || jobs[0] || null
            return {
                jobs,
                currentJob,
                storyboard: currentJob?.storyboard?.scenes || state.storyboard,
                error: currentJob?.errorMessage || state.error,
            }
        })
    },

    loadJob: async (jobId) => {
        const response = await apiFetch<VideoGenerationApiResponse>(`/video-generations/${jobId}`)
        const job = mapJob(response)
        set((state) => ({
            currentJob: job,
            storyboard: job.storyboard?.scenes || [],
            jobs: [job, ...state.jobs.filter((item) => item.id !== job.id)],
            error: job.errorMessage,
        }))
    },

    renameJob: async (jobId, title) => {
        const trimmedTitle = title.trim()
        if (!trimmedTitle) {
            set({ error: 'Title is required' })
            return
        }

        const response = await apiFetch<VideoGenerationApiResponse>(`/video-generations/${jobId}`, {
            method: 'PATCH',
            body: JSON.stringify({ title: trimmedTitle }),
        })
        const job = mapJob(response)
        set((state) => ({
            currentJob: state.currentJob?.id === job.id ? job : state.currentJob,
            storyboard:
                state.currentJob?.id === job.id
                    ? job.storyboard?.scenes || []
                    : state.storyboard,
            jobs: state.jobs.map((item) => (item.id === job.id ? job : item)),
            error: null,
        }))
    },

    deleteJob: async (jobId) => {
        await apiFetch(`/video-generations/${jobId}`, {
            method: 'DELETE',
        })
        set((state) => {
            const jobs = state.jobs.filter((job) => job.id !== jobId)
            const currentJob = state.currentJob?.id === jobId ? jobs[0] || null : state.currentJob
            return {
                jobs,
                currentJob,
                storyboard: currentJob?.storyboard?.scenes || [],
                error: null,
            }
        })
    },

    generateVideo: async () => {
        const form = get().form
        const prompt = form.prompt.trim()
        if (!prompt) {
            set({ error: 'Prompt is required' })
            return
        }

        set({
            isGenerating: true,
            error: null,
            currentJob: null,
            storyboard: [],
            statusSteps: [],
        })

        let jobId: number | null = null

        try {
            await apiFetchStream(
                '/video-generations/render',
                {
                    method: 'POST',
                    body: JSON.stringify({
                        prompt,
                        duration_seconds: form.durationSeconds,
                        fps: form.fps,
                        aspect_ratio: form.aspectRatio,
                        style: form.style,
                        web_search_enabled: form.webSearchEnabled,
                    }),
                },
                (evt: StreamEvent) => {
                    if (evt.event === 'status') {
                        const message =
                            typeof evt.data === 'string' ? evt.data : evt.data?.message
                        jobId = evt.data?.job_id || jobId
                        if (!message) return
                        set((state) => ({
                            statusSteps: [...state.statusSteps, message],
                        }))
                        return
                    }

                    if (evt.event === 'storyboard') {
                        const scenes = evt.data?.scenes || []
                        set({ storyboard: scenes })
                        return
                    }

                    if (evt.event === 'video_result') {
                        jobId = evt.data?.job_id || jobId
                        const currentJob: VideoGenerationJob = {
                            id: jobId || Date.now(),
                            title: prompt,
                            prompt,
                            style: form.style,
                            aspectRatio: form.aspectRatio,
                            durationSeconds: evt.data?.duration_seconds || form.durationSeconds,
                            fps: evt.data?.fps || form.fps,
                            webSearchEnabled: form.webSearchEnabled,
                            status: 'completed',
                            progress: 100,
                            storyboard: { scenes: get().storyboard },
                            sources: null,
                            videoUrl: evt.data?.video_url || null,
                            thumbnailUrl: evt.data?.thumbnail_url || null,
                            errorMessage: null,
                            createdAt: Date.now(),
                            updatedAt: Date.now(),
                            completedAt: Date.now(),
                        }
                        set((state) => ({
                            currentJob,
                            jobs: [currentJob, ...state.jobs.filter((job) => job.id !== currentJob.id)],
                        }))
                        return
                    }

                    if (evt.event === 'done') {
                        set({ isGenerating: false, statusSteps: [] })
                        return
                    }

                    if (evt.event === 'error') {
                        const message =
                            typeof evt.data === 'string'
                                ? evt.data
                                : evt.data?.message || 'Video generation failed'
                        set({ error: message, isGenerating: false })
                    }
                }
            )

            if (jobId) {
                await get().loadJob(jobId)
            }
        } catch (error) {
            set({
                error: error instanceof Error ? error.message : 'Video generation failed',
            })
            throw error
        } finally {
            set({ isGenerating: false })
        }
    },
}))
