import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Download, FileText, FileImage, FileSpreadsheet, Presentation, File as FileIcon } from 'lucide-react'

interface FileViewerProps {
  isOpen: boolean
  onClose: () => void
  fileUrl: string
  filename: string
}

export function FileViewer({ isOpen, onClose, fileUrl, filename }: FileViewerProps) {
  const [content, setContent] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const ext = filename.split('.').pop()?.toLowerCase() || ''
  
  const isImage = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'].includes(ext)
  const isPdf = ext === 'pdf'
  const isText = ['txt', 'md', 'json', 'csv', 'html', 'js', 'py', 'css'].includes(ext)
  const isOffice = ['docx', 'xlsx', 'pptx'].includes(ext)

  useEffect(() => {
    if (isOpen && isText) {
      setLoading(true)
      fetch(fileUrl)
        .then(res => res.text())
        .then(text => {
          setContent(text)
          setLoading(false)
        })
        .catch(_err => {
          setError('Failed to load file content')
          setLoading(false)
        })
    }
  }, [isOpen, fileUrl, isText])

  const getFileIcon = () => {
    if (isImage) return <FileImage className="h-6 w-6" />
    if (isPdf) return <FileText className="h-6 w-6 text-red-500" />
    if (ext === 'xlsx') return <FileSpreadsheet className="h-6 w-6 text-green-500" />
    if (ext === 'pptx') return <Presentation className="h-6 w-6 text-orange-500" />
    if (ext === 'docx') return <FileText className="h-6 w-6 text-blue-500" />
    return <FileIcon className="h-6 w-6" />
  }

  const renderContent = () => {
    if (loading && isText) {
      return <div className="flex items-center justify-center p-12">Loading...</div>
    }

    if (error) {
      return <div className="flex items-center justify-center p-12 text-red-500">{error}</div>
    }

    if (isImage) {
      return (
        <div className="flex items-center justify-center p-4">
          <img 
            src={fileUrl} 
            alt={filename} 
            className="max-h-[70vh] max-w-full object-contain"
          />
        </div>
      )
    }

    if (isPdf) {
      return (
        <div className="h-[70vh]">
          <iframe
            src={fileUrl}
            className="h-full w-full rounded-lg border"
            title={filename}
          />
        </div>
      )
    }

    if (isText && content) {
      return (
        <div className="h-[70vh] overflow-auto rounded-lg border bg-slate-50 p-4">
          <pre className="whitespace-pre-wrap break-all font-mono text-sm">
            {content}
          </pre>
        </div>
      )
    }

    if (isOffice) {
      // Use Microsoft Office Online Viewer for all office formats
      // Works with SAS URLs (absolute, publicly accessible)
      const absoluteUrl = fileUrl.startsWith('http') ? fileUrl : `${window.location.origin}${fileUrl}`
      const viewerUrl = `https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(absoluteUrl)}`
      return (
        <div className="h-[70vh]">
          <iframe
            src={viewerUrl}
            className="h-full w-full rounded-lg border"
            title={filename}
          />
        </div>
      )
    }

    return (
      <div className="flex flex-col items-center justify-center gap-4 p-12">
        <div className="rounded-2xl bg-slate-100 p-8">
          {getFileIcon()}
        </div>
        <p className="text-center text-slate-600">
          This file type cannot be previewed directly
        </p>
        <Button onClick={() => window.open(fileUrl, '_blank')}>
          <Download className="mr-2 h-4 w-4" />
          Download File
        </Button>
      </div>
    )
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-h-[90vh] max-w-4xl overflow-hidden">
        <DialogHeader className="flex flex-row items-center justify-between border-b pb-4">
          <div className="flex items-center gap-3">
            {getFileIcon()}
            <DialogTitle className="text-lg font-semibold">{filename}</DialogTitle>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => window.open(fileUrl, '_blank')}
              className="rounded-xl"
            >
              <Download className="mr-2 h-4 w-4" />
              Download
            </Button>
          </div>
        </DialogHeader>
        <div className="mt-4">
          {renderContent()}
        </div>
      </DialogContent>
    </Dialog>
  )
}
