import { useState } from 'react'
import { Upload, FileJson, X } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface GenericFileUploadProps {
  stepId: number
  acceptedExtensions: string[]
  description: string
  onUpload: (files: FileList, stepId: number) => Promise<void>
  isUploading: boolean
  disabled?: boolean
}

export const GenericFileUpload = ({
  stepId,
  acceptedExtensions,
  description,
  onUpload,
  isUploading,
  disabled = false,
}: GenericFileUploadProps) => {
  const [files, setFiles] = useState<FileList | null>(null)
  const [isDragging, setIsDragging] = useState(false)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFiles(e.target.files)
    }
  }

  const handleUpload = async () => {
    if (!files) return
    await onUpload(files, stepId)
    setFiles(null)
  }

  const handleClear = () => {
    setFiles(null)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    if (!disabled) {
      setIsDragging(true)
    }
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    if (disabled || !e.dataTransfer.files || e.dataTransfer.files.length === 0) return

    // Filter files by accepted extensions
    const acceptedFiles = Array.from(e.dataTransfer.files).filter((file) =>
      acceptedExtensions.some((ext) => file.name.endsWith(ext))
    )

    if (acceptedFiles.length > 0) {
      const dataTransfer = new DataTransfer()
      acceptedFiles.forEach((file) => dataTransfer.items.add(file))
      setFiles(dataTransfer.files)
    }
  }

  const acceptAttribute = acceptedExtensions.join(',')

  return (
    <div className="space-y-4">
      <div
        className={`p-6 border-2 border-dashed rounded-lg transition-colors ${
          disabled
            ? 'border-gray-200 bg-gray-100 cursor-not-allowed opacity-60'
            : isDragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 bg-gray-50'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="flex flex-col items-center justify-center gap-3">
          <label className={`${disabled ? 'cursor-not-allowed' : 'cursor-pointer'} flex flex-col items-center`}>
            <input
              type="file"
              multiple
              accept={acceptAttribute}
              onChange={handleFileChange}
              className="hidden"
              disabled={disabled || isUploading}
            />
            <div className={`flex flex-col items-center gap-2 ${disabled ? 'text-gray-400' : 'text-gray-500 hover:text-gray-700'} transition-colors`}>
              <Upload className="w-8 h-8" />
              <div className="text-center">
                <p className="text-xs font-medium">
                  Drop files here or click to upload
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  {description} ({acceptedExtensions.join(', ')})
                </p>
              </div>
            </div>
          </label>
        </div>
      </div>

      {files && files.length > 0 && (
        <div className="space-y-2">
          <div className="max-h-32 overflow-y-auto space-y-1">
            {Array.from(files).map((file, idx) => (
              <div
                key={idx}
                className="flex items-center gap-2 p-2 bg-white rounded border border-gray-200"
              >
                <FileJson className="w-4 h-4 text-blue-500 flex-shrink-0" />
                <span className="text-xs text-gray-700 flex-1 truncate">
                  {file.name}
                </span>
                <span className="text-xs text-gray-500 flex-shrink-0">
                  {(file.size / 1024).toFixed(1)} KB
                </span>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between gap-2">
            <p className="text-xs text-gray-600">
              {files.length} file{files.length !== 1 ? 's' : ''} selected
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleClear}
                disabled={isUploading}
              >
                <X className="h-3 w-3 mr-1" />
                Clear
              </Button>
              <Button
                size="sm"
                onClick={handleUpload}
                disabled={isUploading}
              >
                {isUploading ? 'Uploading...' : 'Upload & Start'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
