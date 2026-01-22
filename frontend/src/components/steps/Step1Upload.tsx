import { useState } from 'react'
import { Upload, FileJson } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface Step1UploadProps {
  onUpload: (files: FileList) => Promise<void>
  isUploading: boolean
}

export const Step1Upload = ({ onUpload, isUploading }: Step1UploadProps) => {
  const [files, setFiles] = useState<FileList | null>(null)
  const [isDragging, setIsDragging] = useState(false)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFiles(e.target.files)
    }
  }

  const handleUpload = async () => {
    if (!files) return
    await onUpload(files)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      // Filter only JSON files
      const jsonFiles = Array.from(e.dataTransfer.files).filter((file) =>
        file.name.endsWith('.json')
      )

      if (jsonFiles.length > 0) {
        const dataTransfer = new DataTransfer()
        jsonFiles.forEach((file) => dataTransfer.items.add(file))
        setFiles(dataTransfer.files)
      }
    }
  }

  return (
    <div className="space-y-4">
      <div
        className={`p-8 border-2 border-dashed rounded-lg transition-colors ${
          isDragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 bg-gray-50'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="flex flex-col items-center justify-center gap-4">
          <label className="cursor-pointer flex flex-col items-center">
            <input
              type="file"
              multiple
              accept=".json"
              onChange={handleFileChange}
              className="hidden"
              disabled={isUploading}
            />
            <div className="flex flex-col items-center gap-3 text-gray-500 hover:text-gray-700 transition-colors">
              <Upload className="w-12 h-12" />
              <div className="text-center">
                <p className="text-sm font-medium">
                  Click to upload or drag and drop
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  Raw transcript files (.json only)
                </p>
              </div>
            </div>
          </label>
        </div>
      </div>

      {files && files.length > 0 && (
        <div className="space-y-3">
          <div className="max-h-48 overflow-y-auto space-y-2">
            {Array.from(files).map((file, idx) => (
              <div
                key={idx}
                className="flex items-center gap-2 p-2 bg-white rounded border border-gray-200"
              >
                <FileJson className="w-4 h-4 text-blue-500" />
                <span className="text-sm text-gray-700 flex-1 truncate">
                  {file.name}
                </span>
                <span className="text-xs text-gray-500">
                  {(file.size / 1024).toFixed(1)} KB
                </span>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-gray-200">
            <p className="text-sm text-gray-600">
              {files.length} file{files.length !== 1 ? 's' : ''} selected
            </p>
            <Button
              onClick={handleUpload}
              disabled={isUploading}
              className="min-w-32"
            >
              {isUploading ? 'Uploading...' : 'Upload & Start Pipeline'}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
