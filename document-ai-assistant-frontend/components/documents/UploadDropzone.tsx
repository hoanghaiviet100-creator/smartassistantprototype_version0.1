import { ArrowRight, UploadCloud } from "lucide-react";
import type { KeyboardEvent } from "react";

interface UploadDropzoneProps {
  onBrowse: () => void;
  onFilesAdded: (files: FileList | File[] | null) => void;
}

export function UploadDropzone({ onBrowse, onFilesAdded }: UploadDropzoneProps) {
  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onBrowse();
    }
  }

  return (
    <div
      className="upload-zone"
      onClick={onBrowse}
      role="button"
      tabIndex={0}
      onKeyDown={handleKeyDown}
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        event.preventDefault();
        onFilesAdded(event.dataTransfer.files);
      }}
      aria-label="Upload PDF or image files"
    >
      <div className="upload-icon"><UploadCloud size={19} /></div>
      <strong>Drop files or browse</strong>
      <span>PDF, PNG, JPG up to 20 MB</span>
      <span className="upload-link">Choose files <ArrowRight size={13} /></span>
    </div>
  );
}
