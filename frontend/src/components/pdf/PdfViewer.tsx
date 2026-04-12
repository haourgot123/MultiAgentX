import '@/lib/pdf-setup'
import { useState, useCallback, useRef, useEffect } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import { Button } from '@/components/ui/button'
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut } from 'lucide-react'
import type { HighlightRegion } from '@/lib/retrieval-api'

type PdfViewerProps = {
    url: string
    highlights?: HighlightRegion[]
    targetPage?: number
    /** Pass a unique value each time you want to trigger a scroll (e.g. an incrementing counter). */
    targetHighlightIndex?: number
    onDocumentLoad?: ({ numPages }: { numPages: number }) => void
}

export function PdfViewer({ url, highlights = [], targetPage, targetHighlightIndex, onDocumentLoad }: PdfViewerProps) {
    const [numPages, setNumPages] = useState(0)
    const [internalPage, setInternalPage] = useState(1)
    const [scale, setScale] = useState(1.2)
    const [pageHeights, setPageHeights] = useState<Record<number, number>>({})
    const [pageWidths, setPageWidths] = useState<Record<number, number>>({})
    const pageRefs = useRef<Record<number, HTMLDivElement | null>>({})
    const highlightRefs = useRef<Record<string, HTMLDivElement | null>>({})

    const pageNumber = targetPage ?? internalPage

    // Scroll to the target page and its first highlight whenever targetPage or targetHighlightIndex changes
    useEffect(() => {
        if (targetPage === undefined || targetPage < 1) return

        const tryScroll = () => {
            const pageEl = pageRefs.current[targetPage]
            if (!pageEl) return
            pageEl.scrollIntoView({ behavior: 'smooth', block: 'start' })

            // After scrolling to the page, try to scroll to the first highlight on that page
            const attemptScrollToHighlight = (retries: number) => {
                requestAnimationFrame(() => {
                    const refKey = `page-${targetPage}-hl-0`
                    const highlightEl = highlightRefs.current[refKey]
                    if (highlightEl) {
                        highlightEl.scrollIntoView({ behavior: 'smooth', block: 'center' })
                    } else if (retries > 0) {
                        setTimeout(() => attemptScrollToHighlight(retries - 1), 200)
                    }
                })
            }
            attemptScrollToHighlight(10)
        }

        setTimeout(tryScroll, 300)
        // targetHighlightIndex is used as a "scroll trigger" — a new value forces this effect to re-run
    }, [targetPage, targetHighlightIndex, highlights])

    const onDocumentLoadSuccess = useCallback(({ numPages: total }: { numPages: number }) => {
        setNumPages(total)
        onDocumentLoad?.({ numPages: total })
    }, [onDocumentLoad])

    const goToPrevPage = () => setInternalPage((prev) => Math.max(prev - 1, 1))
    const goToNextPage = () => setInternalPage((prev) => Math.min(prev + 1, numPages))
    const zoomIn = () => setScale((prev) => Math.min(prev + 0.2, 3))
    const zoomOut = () => setScale((prev) => Math.max(prev - 0.2, 0.4))

    const handlePageLoadSuccess = useCallback((pageNum: number, page: pdfjs.PDFPageProxy) => {
        const viewport = page.getViewport({ scale: 1 })
        setPageHeights((prev) => ({ ...prev, [pageNum]: viewport.height }))
        setPageWidths((prev) => ({ ...prev, [pageNum]: viewport.width }))
    }, [])

    return (
        <div className="h-full flex flex-col">
            <div className="flex items-center justify-center gap-2 px-3 py-1.5 border-b border-border bg-white shrink-0">
                <Button variant="ghost" size="icon" className="h-7 w-7" onClick={goToPrevPage} disabled={pageNumber <= 1}>
                    <ChevronLeft className="h-4 w-4" />
                </Button>
                <span className="text-xs text-text-muted min-w-[80px] text-center">
                    {pageNumber} / {numPages}
                </span>
                <Button variant="ghost" size="icon" className="h-7 w-7" onClick={goToNextPage} disabled={pageNumber >= numPages}>
                    <ChevronRight className="h-4 w-4" />
                </Button>
                <div className="w-px h-4 bg-border mx-1" />
                <Button variant="ghost" size="icon" className="h-7 w-7" onClick={zoomOut} disabled={scale <= 0.4}>
                    <ZoomOut className="h-4 w-4" />
                </Button>
                <span className="text-xs text-text-muted min-w-[40px] text-center">{Math.round(scale * 100)}%</span>
                <Button variant="ghost" size="icon" className="h-7 w-7" onClick={zoomIn} disabled={scale >= 3}>
                    <ZoomIn className="h-4 w-4" />
                </Button>
            </div>

            <div className="flex-1 overflow-auto bg-surface">
                <Document file={url} onLoadSuccess={onDocumentLoadSuccess} loading={
                    <div className="flex items-center justify-center h-64">
                        <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" />
                    </div>
                }>
                    <div className="flex flex-col items-center gap-4 py-4">
                        {Array.from({ length: numPages }, (_, i) => {
                            const pageNum = i + 1
                            const pageHighlights = highlights.filter((h) => h.pageNo === pageNum)
                            const pageNaturalHeight = pageHeights[pageNum]
                            const isTargetPage = targetPage === pageNum

                            // Flatten all bboxes for this page into a single array for consistent ref indexing
                            let flatBboxIndex = 0

                            return (
                                <div
                                    key={pageNum}
                                    ref={(el) => { pageRefs.current[pageNum] = el }}
                                    className="relative shadow-md bg-white"
                                    style={{ width: 'fit-content' }}
                                >
                                    <Page
                                        pageNumber={pageNum}
                                        scale={scale}
                                        renderTextLayer={false}
                                        renderAnnotationLayer={false}
                                        onLoadSuccess={(page) => handlePageLoadSuccess(pageNum, page)}
                                    />
                                    {pageHighlights.length > 0 && pageNaturalHeight != null && pageHighlights.map((region) =>
                                        region.bboxes.map((bbox, bidx) => {
                                            const left = bbox.x0 * scale
                                            const top = (pageNaturalHeight - bbox.y1) * scale
                                            const width = (bbox.x1 - bbox.x0) * scale
                                            const height = (bbox.y1 - bbox.y0) * scale

                                            const currentIndex = flatBboxIndex++
                                            const refKey = `page-${pageNum}-hl-${currentIndex}`
                                            const isTarget = isTargetPage && currentIndex === 0

                                            return (
                                                <div
                                                    key={`highlight-${pageNum}-${currentIndex}`}
                                                    ref={(el) => { highlightRefs.current[refKey] = el }}
                                                    className={`absolute pointer-events-none animate-in fade-in duration-300 ${isTarget ? 'ring-2 ring-amber-500 ring-offset-1' : ''}`}
                                                    style={{
                                                        left: `${left}px`,
                                                        top: `${top}px`,
                                                        width: `${width}px`,
                                                        height: `${height}px`,
                                                        backgroundColor: 'rgba(250, 204, 21, 0.35)',
                                                        border: '2px solid rgba(245, 158, 11, 0.7)',
                                                        borderRadius: '2px',
                                                    }}
                                                />
                                            )
                                        })
                                    )}
                                </div>
                            )
                        })}
                    </div>
                </Document>
            </div>
        </div>
    )
}