import { Html5Qrcode } from "html5-qrcode";
import { useEffect, useRef } from "react";

export default function QrScanner({ onScan }: { onScan: (text: string) => void }) {
  const containerId = "qr-reader";
  const scannerRef = useRef<Html5Qrcode | null>(null);

  useEffect(() => {
    const scanner = new Html5Qrcode(containerId);
    scannerRef.current = scanner;
    let isStarted = false;

    scanner
      .start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 250, height: 250 } },
        (decodedText) => {
          onScan(decodedText);
        },
        () => {
          // Ignore routine scan frame failures
        },
      )
      .then(() => {
        isStarted = true;
      })
      .catch((err) => {
        console.error("Scanner failed to start", err);
      });

    return () => {
      if (isStarted) {
        scanner.stop().catch(console.error);
      }
    };
  }, [onScan]);

  return (
    <div className="overflow-hidden rounded-md border border-slate-200 bg-black">
      <div id={containerId} className="w-full" />
    </div>
  );
}
