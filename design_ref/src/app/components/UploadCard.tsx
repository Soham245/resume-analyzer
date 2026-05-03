import { Upload, FileText } from 'lucide-react';
import { useState } from 'react';

interface UploadCardProps {
  onFileUpload: (file: File) => void;
}

export function UploadCard({ onFileUpload }: UploadCardProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file && (file.type === 'application/pdf' || file.name.endsWith('.pdf'))) {
      setFileName(file.name);
      onFileUpload(file);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setFileName(file.name);
      onFileUpload(file);
    }
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`
        relative border-2 border-dashed rounded-lg p-8 transition-all
        ${isDragging
          ? 'border-primary bg-accent/50'
          : 'border-border bg-card hover:border-primary/50 hover:bg-accent/20'
        }
      `}
    >
      <input
        type="file"
        accept=".pdf"
        onChange={handleFileInput}
        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
      />

      <div className="flex flex-col items-center justify-center gap-3 pointer-events-none">
        {fileName ? (
          <>
            <FileText className="w-10 h-10 text-primary" />
            <div className="text-center">
              <p className="text-sm text-foreground">{fileName}</p>
              <p className="text-xs text-muted-foreground mt-1">Click or drag to replace</p>
            </div>
          </>
        ) : (
          <>
            <Upload className="w-10 h-10 text-muted-foreground" />
            <div className="text-center">
              <p className="text-sm text-foreground">Drop your resume here</p>
              <p className="text-xs text-muted-foreground mt-1">or click to browse (PDF only)</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
