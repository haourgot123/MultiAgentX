import { apiFetch } from '@/lib/api'

export type RetrievalRecordResponse = {
    id: number
    chunk_id: string
    file_id: number
    file_name: string | null
    chunk_index: number
    citation_label: string
    page_no: number | null
    bbox_json: string | null
    chunk_text: string | null
    relevance_score: string | null
}

export type BBoxItem = {
    page_no: number
    bbox: {
        x0: number
        y0: number
        x1: number
        y1: number
    }
}

export type HighlightRegion = {
    pageNo: number
    bboxes: Array<{
        x0: number
        y0: number
        x1: number
        y1: number
    }>
}

export function parseBBoxJson(bboxJson: string | null): BBoxItem[] {
    if (!bboxJson) return []
    try {
        const parsed: unknown = JSON.parse(bboxJson)
        if (!Array.isArray(parsed)) return []
        return parsed.filter(
            (item: unknown) => {
                if (typeof item !== 'object' || item === null) return false
                const obj = item as Record<string, unknown>
                return (
                    typeof obj.page_no === 'number' &&
                    typeof obj.bbox === 'object' && obj.bbox !== null
                )
            }
        ).map((item) => {
            const obj = item as Record<string, unknown>
            const bbox = obj.bbox as Record<string, unknown>
            return {
                page_no: obj.page_no as number,
                bbox: {
                    x0: bbox.x0 as number,
                    y0: bbox.y0 as number,
                    x1: bbox.x1 as number,
                    y1: bbox.y1 as number,
                },
            }
        }).filter((item) =>
            typeof item.bbox.x0 === 'number' &&
            typeof item.bbox.y0 === 'number' &&
            typeof item.bbox.x1 === 'number' &&
            typeof item.bbox.y1 === 'number'
        )
    } catch {
        return []
    }
}

export function groupHighlightsByPage(bboxItems: BBoxItem[]): HighlightRegion[] {
    const pageMap = new Map<number, Array<{ x0: number; y0: number; x1: number; y1: number }>>()

    for (const item of bboxItems) {
        let { x0, y0, x1, y1 } = item.bbox

        // Normalise: ensure x0 < x1 and y0 < y1
        if (x0 > x1) { const tmp = x0; x0 = x1; x1 = tmp }
        if (y0 > y1) { const tmp = y0; y0 = y1; y1 = tmp }

        // Add padding (in PDF points) so highlights have some breathing room
        const pad = 3
        x0 = Math.max(0, x0 - pad)
        y0 = Math.max(0, y0 - pad)
        x1 = x1 + pad
        y1 = y1 + pad

        // Enforce minimum height so thin baseline boxes still show as visible blocks
        const minH = 14
        if (y1 - y0 < minH) {
            const center = (y0 + y1) / 2
            y0 = center - minH / 2
            y1 = center + minH / 2
        }

        if (!pageMap.has(item.page_no)) {
            pageMap.set(item.page_no, [])
        }
        pageMap.get(item.page_no)!.push({ x0, y0, x1, y1 })
    }

    // Merge overlapping/adjacent bboxes on the same page into continuous blocks
    const regions: HighlightRegion[] = []
    for (const [pageNo, bboxes] of pageMap.entries()) {
        regions.push({ pageNo, bboxes: mergeBboxes(bboxes) })
    }
    return regions
}

/**
 * Merge bboxes that overlap vertically or are within a small gap.
 * This turns per-line highlights into continuous paragraph/block highlights.
 */
function mergeBboxes(bboxes: Array<{ x0: number; y0: number; x1: number; y1: number }>): Array<{ x0: number; y0: number; x1: number; y1: number }> {
    if (bboxes.length <= 1) return bboxes

    // Sort by top (y0), then left (x0)
    const sorted = [...bboxes].sort((a, b) => a.y0 - b.y0 || a.x0 - b.x0)

    const merged: Array<{ x0: number; y0: number; x1: number; y1: number }> = []
    let current = { ...sorted[0] }

    for (let i = 1; i < sorted.length; i++) {
        const next = sorted[i]
        // If next bbox overlaps vertically with current (or gap is very small), merge
        const gap = 6 // merge if within 6pt vertical gap
        if (next.y0 <= current.y1 + gap) {
            // Merge: expand current to encompass both
            current.x0 = Math.min(current.x0, next.x0)
            current.y0 = Math.min(current.y0, next.y0)
            current.x1 = Math.max(current.x1, next.x1)
            current.y1 = Math.max(current.y1, next.y1)
        } else {
            merged.push(current)
            current = { ...next }
        }
    }
    merged.push(current)

    return merged
}

export async function fetchRetrievalRecords(
    conversationId: number,
    messageId: number
): Promise<RetrievalRecordResponse[]> {
    return apiFetch<RetrievalRecordResponse[]>(
        `/conversations/${conversationId}/messages/${messageId}/retrievals`
    )
}