import logoUrl from "@/assets/psense-logo.svg";
import { cn } from "@/lib/utils";

interface PsenseLogoProps {
  className?: string;
  /** When true, renders white via CSS filter for dark backgrounds. */
  invert?: boolean;
  alt?: string;
}

export function PsenseLogo({ className, invert, alt = "PSense.ai" }: PsenseLogoProps) {
  return (
    <img
      src={logoUrl}
      alt={alt}
      className={cn(invert && "brightness-0 invert", className)}
      draggable={false}
    />
  );
}
