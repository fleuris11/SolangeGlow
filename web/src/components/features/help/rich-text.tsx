import { Fragment } from "react";

/**
 * Texts written by the team in the admin (pages, FAQ answers): « # » for a heading,
 * « - » for a list, a blank line between paragraphs. Shown as text, never as HTML.
 */
export function RichText({ text }: { text: string }) {
  const blocks = text.replace(/\r\n/g, "\n").split(/\n{2,}/);
  return (
    <div className="flex flex-col gap-4">
      {blocks.map((block, index) => {
        const trimmed = block.trim();
        if (!trimmed) return null;
        if (trimmed.startsWith("## ")) {
          return (
            <h3 key={index} className="text-lead font-bold">
              {trimmed.slice(3)}
            </h3>
          );
        }
        if (trimmed.startsWith("# ")) {
          return (
            <h2 key={index} className="text-title font-bold">
              {trimmed.slice(2)}
            </h2>
          );
        }
        const lines = trimmed.split("\n");
        if (lines.every((line) => line.startsWith("- "))) {
          return (
            <ul key={index} className="flex list-disc flex-col gap-1 pl-6">
              {lines.map((line, at) => (
                <li key={at}>{line.slice(2)}</li>
              ))}
            </ul>
          );
        }
        return (
          <p key={index}>
            {lines.map((line, at) => (
              <Fragment key={at}>
                {at > 0 && <br />}
                {line}
              </Fragment>
            ))}
          </p>
        );
      })}
    </div>
  );
}
