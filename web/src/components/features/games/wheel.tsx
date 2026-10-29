"use client";

import { Disc } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Bloom } from "@/components/ui/bloom";
import { Button, buttonClasses } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { getWheel, spinWheel, type Wheel, type WheelSpin } from "@/lib/api/games";
import { Link } from "@/lib/i18n/navigation";

const FILLS = ["var(--hibiscus)", "var(--or)", "var(--poudre)", "var(--carte)"];
const TEXT = ["var(--sur-hibiscus)", "var(--sur-or)", "var(--prune)", "var(--prune)"];
const SPIN_MS = 3200;

function reduced() {
  return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
}

/** The slices, all the same size (the chances are written below, in words). */
function Disk({ wheel, rotation, moving }: { wheel: Wheel; rotation: number; moving: boolean }) {
  const count = Math.max(wheel.prizes.length, 1);
  const angle = 360 / count;
  const point = (degrees: number, radius: number) => {
    const rad = ((degrees - 90) * Math.PI) / 180;
    return [100 + radius * Math.cos(rad), 100 + radius * Math.sin(rad)];
  };
  return (
    <div className="relative mx-auto w-full max-w-80">
      <svg
        viewBox="0 0 24 24"
        aria-hidden
        className="absolute -top-1 left-1/2 z-10 size-10 -translate-x-1/2"
      >
        <path d="M12 22 L4 4 H20 Z" fill="var(--prune)" />
      </svg>
      <svg
        viewBox="0 0 200 200"
        aria-hidden
        className="w-full"
        style={{
          transform: `rotate(${rotation}deg)`,
          transition: moving ? `transform ${SPIN_MS}ms cubic-bezier(0.17, 0.67, 0.2, 1)` : "none",
        }}
      >
        <circle cx="100" cy="100" r="99" fill="var(--trait)" />
        {wheel.prizes.map((prize, index) => {
          const [x1, y1] = point(index * angle, 96);
          const [x2, y2] = point((index + 1) * angle, 96);
          const [tx, ty] = point(index * angle + angle / 2, 62);
          const large = angle > 180 ? 1 : 0;
          return (
            <g key={prize.id}>
              <path
                d={`M100 100 L${x1} ${y1} A96 96 0 ${large} 1 ${x2} ${y2} Z`}
                fill={FILLS[index % FILLS.length]}
                stroke="var(--trait)"
              />
              <text
                x={tx}
                y={ty}
                fill={TEXT[index % TEXT.length]}
                fontSize="9"
                fontWeight="700"
                textAnchor="middle"
                dominantBaseline="middle"
                transform={`rotate(${index * angle + angle / 2} ${tx} ${ty})`}
              >
                {prize.label.length > 16 ? `${prize.label.slice(0, 15)}…` : prize.label}
              </text>
            </g>
          );
        })}
        <circle cx="100" cy="100" r="14" fill="var(--prune)" />
      </svg>
    </div>
  );
}

/** The Glow wheel: one free spin a day, the server draws, the wheel shows the result. */
export function WheelScreen() {
  const t = useTranslations("games.wheel");
  const toast = useToast();
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["glow-wheel"], queryFn: getWheel });
  const [rotation, setRotation] = useState(0);
  const [moving, setMoving] = useState(false);
  const [result, setResult] = useState<WheelSpin | null>(null);

  if (query.isPending) return <Skeleton className="rounded-card h-96" />;
  const wheel = query.data;
  if (!wheel || !wheel.open || wheel.prizes.length === 0) {
    return (
      <EmptyState
        icon={<Disc size={48} weight="duotone" />}
        title={t("closed")}
        action={
          <Link href="/points" className={buttonClasses({ variant: "secondary" })}>
            {t("back")}
          </Link>
        }
      />
    );
  }
  const shown = result ?? wheel.today;

  const spin = async () => {
    try {
      const won = await spinWheel();
      const index = Math.max(
        0,
        wheel.prizes.findIndex((prize) => prize.id === won.prize_id),
      );
      const angle = 360 / wheel.prizes.length;
      // The pointer is at the top: the middle of the slice won comes under it.
      const target = 360 * 5 + (360 - (index * angle + angle / 2));
      if (reduced()) {
        setRotation(target % 360);
        setResult(won);
      } else {
        setMoving(true);
        setRotation(target);
        window.setTimeout(() => {
          setMoving(false);
          setResult(won);
        }, SPIN_MS);
      }
      client.invalidateQueries({ queryKey: ["glow-me"] });
      client.invalidateQueries({ queryKey: ["glow-vouchers"] });
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start gap-2">
        <h1 className="text-headline flex-1 font-bold">{t("title")}</h1>
        <SpeakButton text={`${t("title")}. ${t("free")}`} />
      </div>
      <p className="text-prune-doux">{t("free")}</p>
      <Disk wheel={wheel} rotation={rotation} moving={moving} />

      {shown ? (
        <div aria-live="polite" className="flex flex-col items-center gap-3 text-center">
          {result && result.kind !== "nothing" && (
            <Bloom label={t("won", { prize: result.label })} />
          )}
          <p className="text-lead font-bold">
            {shown.kind === "nothing" ? t("nothing") : t("won", { prize: shown.label })}
          </p>
          {shown.voucher && (
            <p className="flex flex-col">
              <span className="text-small">{t("voucher")}</span>
              <span className="font-display text-headline font-black tracking-widest">
                {shown.voucher.code}
              </span>
            </p>
          )}
          <p className="text-prune-doux">{t("tomorrow")}</p>
          <Link href="/points" className={buttonClasses({ variant: "secondary", fullWidth: true })}>
            {t("back")}
          </Link>
        </div>
      ) : (
        <Button size="lg" fullWidth onClick={spin} disabled={moving || !wheel.can_spin}>
          <Disc aria-hidden size={24} weight="bold" />
          {moving ? t("spinning") : t("spin")}
        </Button>
      )}

      <section aria-labelledby="chances-title" className="flex flex-col gap-2">
        <h2 id="chances-title" className="text-title font-bold">
          {t("chances")}
        </h2>
        <ul className="border-trait bg-carte rounded-card divide-trait flex flex-col divide-y border">
          {wheel.prizes.map((prize) => (
            <li key={prize.id} className="flex items-center justify-between gap-3 p-3">
              <span className="font-bold">{prize.label}</span>
              <span>{t("percent", { value: Number(prize.chance) })}</span>
            </li>
          ))}
        </ul>
        <p className="text-small text-prune-doux">{t("rules")}</p>
      </section>
    </div>
  );
}
