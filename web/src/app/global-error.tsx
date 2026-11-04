"use client";

const WORDS = {
  fr: ["Un problème est survenu", "Recharge la page dans un instant.", "Recharger"],
  en: ["Something went wrong", "Reload the page in a moment.", "Reload"],
  sk: ["Nastal problém", "O chvíľu obnov stránku.", "Obnoviť"],
};

/** Last resort, when even the layout fails: no theme and no translation files are available. */
export default function GlobalError({ reset }: { reset: () => void }) {
  const lang = typeof navigator === "undefined" ? "fr" : navigator.language.slice(0, 2);
  const [title, text, retry] = WORDS[lang as keyof typeof WORDS] ?? WORDS.fr;
  return (
    <html lang={lang}>
      <body style={{ fontFamily: "system-ui, sans-serif", margin: 0, padding: 24 }}>
        <main style={{ margin: "20vh auto 0", maxWidth: 480 }}>
          <h1>{title}</h1>
          <p>{text}</p>
          <button type="button" onClick={reset} style={{ minHeight: 48, padding: "0 20px" }}>
            {retry}
          </button>
        </main>
      </body>
    </html>
  );
}
