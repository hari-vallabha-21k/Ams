import { useState } from "react";

import type { IssuedCredential } from "../lib/types";

/** Share, copy, download or print a pass - section 14 of the PRD. */
export default function PassShare({
  credential,
  title,
  message,
}: {
  credential: IssuedCredential;
  title: string;
  message: string;
}) {
  const [copied, setCopied] = useState(false);
  const whatsapp = `https://wa.me/?text=${encodeURIComponent(`${message}\n${credential.pass_url}`)}`;

  const copy = async () => {
    await navigator.clipboard.writeText(credential.pass_url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const download = () => {
    const link = document.createElement("a");
    link.href = credential.qr_image;
    link.download = `${title.replace(/\s+/g, "-").toLowerCase()}-qr.png`;
    link.click();
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col items-center gap-3 rounded-lg border border-slate-200 p-4">
        <img src={credential.qr_image} alt="Pass QR code" className="h-52 w-52" />
        <p className="text-center text-sm font-medium text-slate-700">{title}</p>
        <code className="w-full break-all rounded bg-slate-50 px-2 py-1 text-center text-xs text-slate-500">
          {credential.pass_url}
        </code>
      </div>
      <div className="no-print grid grid-cols-2 gap-2 sm:grid-cols-4">
        <a className="btn-secondary" href={whatsapp} target="_blank" rel="noreferrer">
          Share on WhatsApp
        </a>
        <button className="btn-secondary" onClick={copy}>
          {copied ? "Link copied" : "Copy link"}
        </button>
        <button className="btn-secondary" onClick={download}>
          Download QR
        </button>
        <button className="btn-secondary" onClick={() => window.print()}>
          Print pass
        </button>
      </div>
    </div>
  );
}
