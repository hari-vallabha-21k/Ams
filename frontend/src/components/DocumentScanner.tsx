import { useCallback, useRef } from "react";
import Webcam from "react-webcam";

export default function DocumentScanner({
  onCapture,
  onCancel,
}: {
  onCapture: (file: File) => void;
  onCancel: () => void;
}) {
  const webcamRef = useRef<Webcam>(null);

  const capture = useCallback(() => {
    const imageSrc = webcamRef.current?.getScreenshot();
    if (!imageSrc) return;

    // Convert base64 data URI to a File object
    const byteString = atob(imageSrc.split(",")[1]);
    const mimeString = imageSrc.split(",")[0].split(":")[1].split(";")[0];
    const ab = new ArrayBuffer(byteString.length);
    const ia = new Uint8Array(ab);
    for (let i = 0; i < byteString.length; i++) {
      ia[i] = byteString.charCodeAt(i);
    }
    const blob = new Blob([ab], { type: mimeString });
    const file = new File([blob], `scanned-document-${Date.now()}.jpeg`, {
      type: mimeString,
    });

    onCapture(file);
  }, [onCapture]);

  return (
    <div className="space-y-4">
      <div className="overflow-hidden rounded-md border border-slate-200 bg-black">
        <Webcam
          ref={webcamRef}
          audio={false}
          screenshotFormat="image/jpeg"
          videoConstraints={{ facingMode: "environment" }}
          className="w-full object-contain"
        />
      </div>
      <div className="flex gap-2">
        <button type="button" className="btn-secondary flex-1" onClick={onCancel}>
          Cancel
        </button>
        <button type="button" className="btn-primary flex-1" onClick={capture}>
          Take Photo
        </button>
      </div>
    </div>
  );
}
