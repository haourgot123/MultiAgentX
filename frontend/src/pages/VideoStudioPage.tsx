import { useEffect } from 'react'
import { toast } from 'sonner'

import { VideoPreviewPanel } from '@/components/video/VideoPreviewPanel'
import { VideoSettingsPanel } from '@/components/video/VideoSettingsPanel'
import { useVideoStore } from '@/store/video-store'

export default function VideoStudioPage() {
    const fetchJobs = useVideoStore((state) => state.fetchJobs)

    useEffect(() => {
        void fetchJobs().catch((error) => {
            toast.error(error instanceof Error ? error.message : 'Failed to load videos')
        })
    }, [fetchJobs])

    return (
        <div className="flex h-full min-h-0 w-full">
            <div className="h-full w-[420px] min-w-[360px] max-w-[46vw] shrink-0">
                <VideoSettingsPanel />
            </div>
            <VideoPreviewPanel />
        </div>
    )
}
