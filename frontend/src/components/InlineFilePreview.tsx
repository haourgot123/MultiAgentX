import { useState, useEffect } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Download, Eye, X, FileText, FileImage, FileCode } from 'lucide-react'

interface InlineFilePreviewProps {
  fileUrl: string
  filename: string
  sandboxIndex?: number
  onView?: () => void
  onDownload?: () => void
}

export function InlineFilePreview({ 
  fileUrl, 
  filename, 
  sandboxIndex,
  onView,
  onDownload 
}: InlineFilePreviewProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [content, setContent] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const ext = filename.split('.').pop()?.toLowerCase() || ''
  
  const isImage = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'].includes(ext)
  const isPdf = ext === 'pdf'
  const isHtml = ext === 'html' || ext === 'htm'
  const isText = ['txt', 'md', 'json', 'csv', 'js', 'py', 'css', 'tsx', 'ts', 'jsx'].includes(ext)

  const canPreviewInline = isImage || isHtml || isText || isPdf

  useEffect(() => {
    if (isExpanded && isText && !content) {
      setLoading(true)
      fetch(fileUrl)
        .then(res => res.text())
        .then(text => {
          setContent(text)
          setLoading(false)
        })
        .catch(() => {
          setContent('Failed to load file content')
          setLoading(false)
        })
    }
  }, [isExpanded, fileUrl, isText, content])

  const getFileIcon = () => {
    if (isImage) return <FileImage className="h-4 w-4" />
    if (isText || isHtml) return <FileCode className="h-4 w-4" />
    return <FileText className="h-4 w-4" />
  }

  const handleDownload = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (onDownload) {
      onDownload()
    } else {
      window.open(fileUrl, '_blank')
    }
  }

  const handleToggleExpand = () => {
    if (!canPreviewInline) {
      if (onView) onView()
      return
    }
    setIsExpanded(!isExpanded)
  }

  return (
    <Card className="overflow-hidden border-slate-200">
      <div 
        className="flex items-center justify-between bg-slate-50 px-3 py-2 cursor-pointer hover:bg-slate-100 transition-colors"
        onClick={handleToggleExpand}
      >
        <div className="flex items-center gap-2 min-w-0">
          {getFileIcon()}
          <span className="text-sm font-medium text-slate-700 truncate">
            {filename}
          </span>
          {sandboxIndex !== undefined && (
            <span className="text-xs text-slate-400">
              (Sandbox #{sandboxIndex + 1})
            </span>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {canPreviewInline && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={(e) => {
                e.stopPropagation()
                setIsExpanded(!isExpanded)
              }}
            >
              {isExpanded ? (
                <X className="h-3.5 w-3.5" />
              ) : (
                <Eye className="h-3.5 w-3.5" />
              )}
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={handleDownload}
          >
            <Download className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {isExpanded && canPreviewInline && (
        <div className="border-t border-slate-200">
          {isImage && (
            <div className="flex items-center justify-center bg-slate-100 p-2">
              <img
                src={fileUrl}
                alt={filename}
                className="max-h-[300px] max-w-full object-contain rounded"
              />
            </div>
          )}

          {isHtml && (
            <div className="h-[300px] bg-white">
              <iframe
                src={fileUrl}
                className="h-full w-full"
                title={filename}
                sandbox="allow-scripts"
              />
            </div>
          )}

          {isPdf && (
            <div className="h-[300px] bg-white">
              <iframe
                src={fileUrl}
                className="h-full w-full"
                title={filename}
              />
            </div>
          )}

          {isText && (
            <div className="max-h-[300px] overflow-auto bg-slate-950 p-3">
              {loading ? (
                <div className="text-slate-400 text-sm">Loading...</div>
              ) : (
                <pre className="whitespace-pre-wrap break-words font-mono text-xs text-slate-100">
                  {content}
                </pre>
              )}
            </div>
          )}
        </div>
      )}
    </Card>
  )
}

export default InlineFilePreview
