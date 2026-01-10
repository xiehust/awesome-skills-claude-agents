import { useQuery } from '@tanstack/react-query';
import Modal from '../common/Modal';
import CodePreview from './CodePreview';
import { workspaceService } from '../../services/workspace';
import type { WorkspaceFileContent } from '../../types';

interface FilePreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  agentId: string;
  file: { path: string; name: string } | null;
}

// Image file extensions
const IMAGE_EXTENSIONS = new Set([
  'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'ico', 'bmp'
]);

// Format file size for display
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  let unitIndex = 0;
  let size = bytes;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  return `${size.toFixed(unitIndex > 0 ? 1 : 0)} ${units[unitIndex]}`;
};

// Check if file is an image
const isImageFile = (filename: string): boolean => {
  const ext = filename.split('.').pop()?.toLowerCase();
  return IMAGE_EXTENSIONS.has(ext || '');
};

// Check if content is text based on encoding
const isTextContent = (encoding: string): boolean => {
  return encoding === 'utf-8';
};

// Download file from content
const downloadFile = (filename: string, content: WorkspaceFileContent) => {
  let blob: Blob;

  if (content.encoding === 'base64') {
    // Decode base64 to binary
    const binaryString = atob(content.content);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    blob = new Blob([bytes], { type: content.mimeType });
  } else {
    // Text content
    blob = new Blob([content.content], { type: content.mimeType });
  }

  // Create download link
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

export function FilePreviewModal({ isOpen, onClose, agentId, file }: FilePreviewModalProps) {
  // Fetch file content when modal is open and file is selected
  const {
    data: fileContent,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['workspace-file', agentId, file?.path],
    queryFn: () => workspaceService.readFile(agentId, file!.path),
    enabled: isOpen && !!file && !!agentId,
    staleTime: 60000, // Cache for 1 minute
  });

  // Handle download
  const handleDownload = () => {
    if (file && fileContent) {
      downloadFile(file.name, fileContent);
    }
  };

  // Render content based on type
  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="flex items-center justify-center h-64 text-muted">
          <span className="material-symbols-outlined animate-spin mr-2">
            progress_activity
          </span>
          Loading file...
        </div>
      );
    }

    if (isError) {
      return (
        <div className="flex flex-col items-center justify-center h-64 text-status-error">
          <span className="material-symbols-outlined text-3xl mb-2">error</span>
          <span className="text-sm">
            {error instanceof Error ? error.message : 'Failed to load file'}
          </span>
        </div>
      );
    }

    if (!fileContent || !file) {
      return null;
    }

    // Download button component
    const DownloadButton = () => (
      <button
        onClick={handleDownload}
        className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg transition-colors"
      >
        <span className="material-symbols-outlined text-lg">download</span>
        Download
      </button>
    );

    // Image preview
    if (isImageFile(file.name) && fileContent.encoding === 'base64') {
      return (
        <div className="flex flex-col items-center">
          <img
            src={`data:${fileContent.mimeType};base64,${fileContent.content}`}
            alt={file.name}
            className="max-w-full max-h-[55vh] object-contain rounded-lg border border-dark-border"
          />
          <div className="flex items-center justify-between w-full mt-4">
            <span className="text-sm text-muted">
              {fileContent.mimeType} - {formatFileSize(fileContent.size)}
            </span>
            <DownloadButton />
          </div>
        </div>
      );
    }

    // Text/Code preview
    if (isTextContent(fileContent.encoding)) {
      return (
        <div className="flex flex-col">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-muted">
              {fileContent.mimeType} - {formatFileSize(fileContent.size)}
            </span>
            <DownloadButton />
          </div>
          <CodePreview
            content={fileContent.content}
            filename={file.name}
            showLineNumbers={true}
            className="max-h-[55vh]"
          />
        </div>
      );
    }

    // Binary file (non-image)
    return (
      <div className="flex flex-col items-center justify-center h-64 text-muted">
        <span className="material-symbols-outlined text-5xl mb-4">draft</span>
        <span className="text-lg font-medium mb-2">Binary File</span>
        <span className="text-sm text-center mb-4">
          This file cannot be previewed.
          <br />
          {fileContent.mimeType} - {formatFileSize(fileContent.size)}
        </span>
        <DownloadButton />
      </div>
    );
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={file?.name || 'File Preview'}
      size="3xl"
    >
      {renderContent()}
    </Modal>
  );
}

export default FilePreviewModal;
