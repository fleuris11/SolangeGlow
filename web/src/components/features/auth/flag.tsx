import { GlobeHemisphereWest } from "@phosphor-icons/react/dist/ssr";

/*
 * Flags drawn in SVG: flag emojis do not display on Windows and some Android phones.
 * Official colours of each flag (reference data, not theme colours).
 */
const FLAGS: Record<string, React.ReactNode> = {
  BJ: (
    <>
      <rect width="30" height="20" fill="#FCD116" />
      <rect y="10" width="30" height="10" fill="#E8112D" />
      <rect width="12" height="20" fill="#008751" />
    </>
  ),
  FR: (
    <>
      <rect width="30" height="20" fill="#FFFFFF" />
      <rect width="10" height="20" fill="#002395" />
      <rect x="20" width="10" height="20" fill="#ED2939" />
    </>
  ),
};

export function Flag({ country, className }: { country: string; className?: string }) {
  const drawing = FLAGS[country];
  if (!drawing) {
    return <GlobeHemisphereWest aria-hidden size={22} weight="duotone" className={className} />;
  }
  return (
    <svg
      aria-hidden
      viewBox="0 0 30 20"
      width={30}
      height={20}
      className={className ?? "border-trait shrink-0 rounded-[3px] border"}
      focusable="false"
    >
      {drawing}
    </svg>
  );
}
