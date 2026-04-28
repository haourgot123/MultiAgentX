import { beforeEach, describe, expect, it, vi } from 'vitest'

const { apiFetchMock, apiFetchStreamMock } = vi.hoisted(() => ({
    apiFetchMock: vi.fn(),
    apiFetchStreamMock: vi.fn(),
}))

vi.mock('@/lib/api', () => ({
    apiFetch: apiFetchMock,
    apiFetchStream: apiFetchStreamMock,
}))

import { useVideoStore } from '@/store/video-store'

const resetStore = () => {
    useVideoStore.setState({
        form: {
            prompt: '',
            durationSeconds: 15,
            fps: 30,
            aspectRatio: '16:9',
            style: 'educational',
            webSearchEnabled: true,
        },
        jobs: [],
        currentJob: null,
        storyboard: [],
        statusSteps: [],
        isGenerating: false,
        error: null,
    })
}

describe('useVideoStore', () => {
    beforeEach(() => {
        apiFetchMock.mockReset()
        apiFetchStreamMock.mockReset()
        resetStore()
    })

    it('keeps v1 defaults and clamps duration to 30 seconds', () => {
        expect(useVideoStore.getState().form).toMatchObject({
            durationSeconds: 15,
            fps: 30,
            aspectRatio: '16:9',
            style: 'educational',
            webSearchEnabled: true,
        })

        useVideoStore.getState().setForm({ durationSeconds: 99 })
        expect(useVideoStore.getState().form.durationSeconds).toBe(30)
    })

    it('streams storyboard and video result into preview state', async () => {
        useVideoStore.getState().setForm({
            prompt: 'Create a video about agents',
            durationSeconds: 12,
            fps: 24,
            aspectRatio: '1:1',
            style: 'cinematic',
            webSearchEnabled: false,
        })

        apiFetchStreamMock.mockImplementationOnce(async (_path, _options, onEvent) => {
            onEvent({ event: 'status', data: { job_id: 7, message: 'Creating storyboard...' } })
            onEvent({
                event: 'storyboard',
                data: {
                    scenes: [
                        {
                            index: 1,
                            title: 'Opening',
                            narration: 'Intro',
                            visual_prompt: 'Visual',
                            on_screen_text: 'Agent workflows',
                            duration_seconds: 12,
                        },
                    ],
                },
            })
            onEvent({
                event: 'video_result',
                data: {
                    job_id: 7,
                    video_url: 'https://example.com/video.mp4',
                    thumbnail_url: 'https://example.com/thumb.png',
                    duration_seconds: 12,
                    fps: 24,
                    aspect_ratio: '1:1',
                },
            })
            onEvent({ event: 'done', data: { job_id: 7 } })
        })

        apiFetchMock.mockResolvedValueOnce({
            id: 7,
            prompt: 'Create a video about agents',
            style: 'cinematic',
            aspect_ratio: '1:1',
            duration_seconds: 12,
            fps: 24,
            web_search_enabled: false,
            status: 'completed',
            progress: 100,
            storyboard: {
                scenes: [
                    {
                        index: 1,
                        title: 'Opening',
                        narration: 'Intro',
                        visual_prompt: 'Visual',
                        on_screen_text: 'Agent workflows',
                        duration_seconds: 12,
                    },
                ],
            },
            sources: [],
            video_url: 'https://example.com/video.mp4',
            thumbnail_url: 'https://example.com/thumb.png',
            error_message: null,
            created_at: '2026-04-28T10:00:00Z',
            updated_at: '2026-04-28T10:00:01Z',
            completed_at: '2026-04-28T10:00:01Z',
        })

        await useVideoStore.getState().generateVideo()

        expect(apiFetchStreamMock).toHaveBeenCalledWith(
            '/video-generations/render',
            expect.objectContaining({
                method: 'POST',
                body: JSON.stringify({
                    prompt: 'Create a video about agents',
                    duration_seconds: 12,
                    fps: 24,
                    aspect_ratio: '1:1',
                    style: 'cinematic',
                    web_search_enabled: false,
                }),
            }),
            expect.any(Function)
        )
        expect(useVideoStore.getState().storyboard).toHaveLength(1)
        expect(useVideoStore.getState().currentJob?.videoUrl).toBe('https://example.com/video.mp4')
        expect(useVideoStore.getState().isGenerating).toBe(false)
    })
})
