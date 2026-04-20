/**
 * PSense Mail — Sanitized HTML frame for safe email body rendering.
 *
 * Runs body_html through DOMPurify with a strict allowlist before
 * rendering inside a sandboxed iframe. Blocks external images by
 * default, with a user opt-in "Show images" prompt per message.
 *
 * Falls back to <pre> for plain text, or an empty state when both are null.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import DOMPurify from "dompurify";
import { ImageOff, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";

// Strict DOMPurify config — strip scripts, objects, event handlers
const PURIFY_CONFIG = {
  ALLOWED_TAGS: [
    "a", "abbr", "address", "article", "aside", "b", "bdi", "bdo",
    "blockquote", "br", "caption", "cite", "code", "col", "colgroup",
    "dd", "del", "details", "dfn", "div", "dl", "dt", "em", "figcaption",
    "figure", "footer", "h1", "h2", "h3", "h4", "h5", "h6", "header",
    "hr", "i", "img", "ins", "kbd", "li", "main", "mark", "nav", "ol",
    "p", "pre", "q", "rp", "rt", "ruby", "s", "samp", "section", "small",
    "span", "strong", "sub", "summary", "sup", "table", "tbody", "td",
    "tfoot", "th", "thead", "time", "tr", "u", "ul", "var", "wbr",
    "style",
  ],
  ALLOWED_ATTR: [
    "href", "src", "alt", "title", "class", "id", "style", "dir",
    "lang", "width", "height", "align", "valign", "bgcolor", "border",
    "cellpadding", "cellspacing", "colspan", "rowspan", "scope",
    "target", "rel", "type",
  ],
  FORBID_TAGS: ["script", "object", "embed", "form", "input", "textarea", "button", "select", "iframe"],
  FORBID_ATTR: [
    "onerror", "onload", "onclick", "onmouseover", "onfocus", "onblur",
    "onsubmit", "onchange", "onkeydown", "onkeyup", "onkeypress",
  ],
  ALLOW_DATA_ATTR: false,
};

// CSS to strip images (replace src with empty gif)
const IMAGE_BLOCK_STYLE = `
  img { display: none !important; }
  img[data-blocked="true"] { display: none !important; }
`;

interface SanitizedHtmlFrameProps {
  bodyHtml: string | null | undefined;
  bodyText: string | null | undefined;
  className?: string;
}

export function SanitizedHtmlFrame({
  bodyHtml,
  bodyText,
  className,
}: SanitizedHtmlFrameProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [imagesBlocked, setImagesBlocked] = useState(true);
  const [hasExternalImages, setHasExternalImages] = useState(false);
  const [iframeHeight, setIframeHeight] = useState(200);

  // No body at all
  if (!bodyHtml && !bodyText) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-muted-foreground">
        <FileText className="mb-2 h-8 w-8" aria-hidden />
        <p className="text-sm">No message body</p>
      </div>
    );
  }

  // Plain text only
  if (!bodyHtml && bodyText) {
    return (
      <pre
        className={`whitespace-pre-wrap break-words text-sm leading-relaxed text-foreground/90 ${className ?? ""}`}
      >
        {bodyText}
      </pre>
    );
  }

  // Sanitize HTML
  const sanitizedHtml = useSanitizedHtml(bodyHtml ?? "", imagesBlocked, setHasExternalImages);

  // Resize iframe to content height
  const updateHeight = useCallback(() => {
    const iframe = iframeRef.current;
    if (iframe?.contentDocument?.body) {
      const h = iframe.contentDocument.body.scrollHeight;
      if (h > 0) setIframeHeight(h + 24);
    }
  }, []);

  useEffect(() => {
    const iframe = iframeRef.current;
    if (!iframe) return;

    const doc = iframe.contentDocument;
    if (!doc) return;

    doc.open();
    doc.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <meta charset="utf-8" />
          <style>
            body {
              margin: 0;
              padding: 4px 0;
              font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
              font-size: 14px;
              line-height: 1.6;
              color: #1a1a1a;
              word-break: break-word;
              overflow-wrap: break-word;
            }
            a { color: #2563eb; }
            blockquote {
              border-left: 2px solid #e5e7eb;
              margin-left: 0;
              padding-left: 12px;
              color: #6b7280;
            }
            img { max-width: 100%; height: auto; }
            ${imagesBlocked ? IMAGE_BLOCK_STYLE : ""}
          </style>
        </head>
        <body>${sanitizedHtml}</body>
      </html>
    `);
    doc.close();

    // Wait for content to render, then adjust height
    setTimeout(updateHeight, 100);
    setTimeout(updateHeight, 500);
  }, [sanitizedHtml, imagesBlocked, updateHeight]);

  return (
    <div className={className}>
      {hasExternalImages && imagesBlocked && (
        <div className="mb-2 flex items-center gap-2 rounded-md border border-border bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
          <ImageOff className="h-4 w-4 shrink-0" aria-hidden />
          <span>External images are blocked for your safety.</span>
          <Button
            variant="outline"
            size="sm"
            className="ml-auto h-6 px-2 text-xs"
            onClick={() => setImagesBlocked(false)}
          >
            Show images
          </Button>
        </div>
      )}
      <iframe
        ref={iframeRef}
        sandbox="allow-same-origin"
        title="Email body"
        className="w-full border-0"
        style={{ height: iframeHeight, minHeight: 100 }}
      />
    </div>
  );
}

/**
 * Custom hook that sanitizes HTML through DOMPurify and detects external images.
 */
function useSanitizedHtml(
  html: string,
  blockImages: boolean,
  setHasExternalImages: (v: boolean) => void,
): string {
  const [sanitized, setSanitized] = useState("");

  useEffect(() => {
    let foundExternal = false;

    // Hook into DOMPurify to detect removed elements
    DOMPurify.addHook("uponSanitizeElement", (node, data) => {
      if (data.tagName && !PURIFY_CONFIG.ALLOWED_TAGS?.includes(data.tagName)) {
        console.warn(
          `[PSense Mail] DOMPurify removed element: <${data.tagName}>`
        );
      }
    });

    DOMPurify.addHook("uponSanitizeAttribute", (_node, data) => {
      if (data.attrName && data.attrValue && PURIFY_CONFIG.FORBID_ATTR?.includes(data.attrName)) {
        console.warn(
          `[PSense Mail] DOMPurify removed attribute: ${data.attrName}="${data.attrValue}"`
        );
      }
    });

    // Detect external images
    DOMPurify.addHook("afterSanitizeAttributes", (node) => {
      if (node.tagName === "IMG") {
        const src = node.getAttribute("src") || "";
        if (src.startsWith("http://") || src.startsWith("https://")) {
          foundExternal = true;
          if (blockImages) {
            node.setAttribute("data-blocked", "true");
            node.removeAttribute("src");
          }
        }
      }
      // Force links to open in new tab
      if (node.tagName === "A") {
        node.setAttribute("target", "_blank");
        node.setAttribute("rel", "noopener noreferrer");
      }
    });

    const clean = DOMPurify.sanitize(html, PURIFY_CONFIG) as unknown as string;
    setSanitized(clean);
    setHasExternalImages(foundExternal);

    // Clean up hooks
    DOMPurify.removeAllHooks();
  }, [html, blockImages, setHasExternalImages]);

  return sanitized;
}
