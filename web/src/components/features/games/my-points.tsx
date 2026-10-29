"use client";

import {
  CalendarStar,
  Camera,
  CheckSquare,
  Copy,
  Disc,
  Lightbulb,
  Ranking,
  Scales,
  Ticket,
  WhatsappLogo,
} from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";

import { Bloom } from "@/components/ui/bloom";
import { Button, buttonClasses } from "@/components/ui/button";
import { Sheet } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { ApiError, type Schemas } from "@/lib/api/client";
import {
  getGlowMe,
  getHistory,
  getRewards,
  getVouchers,
  redeemReward,
  type GlowReward,
} from "@/lib/api/games";
import { Link } from "@/lib/i18n/navigation";
import { formatMoney } from "@/lib/money";

import { Flame, LevelBadge, Progress } from "./glow-bits";

const GAMES: { href: string; key: string; icon: ReactNode }[] = [
  { href: "/quiz", key: "quiz", icon: <Lightbulb size={32} weight="duotone" /> },
  { href: "/roue", key: "wheel", icon: <Disc size={32} weight="duotone" /> },
  { href: "/defi", key: "challenge", icon: <Camera size={32} weight="duotone" /> },
  { href: "/choisir", key: "polls", icon: <Scales size={32} weight="duotone" /> },
  { href: "/routine", key: "routine", icon: <CheckSquare size={32} weight="duotone" /> },
  { href: "/fetes", key: "calendar", icon: <CalendarStar size={32} weight="duotone" /> },
  { href: "/classements", key: "rankings", icon: <Ranking size={32} weight="duotone" /> },
];

/** The games of the day, as big tiles (icon + word). */
export function GamesGrid() {
  const t = useTranslations("games.hub");
  return (
    <nav aria-label={t("title")}>
      <ul className="grid grid-cols-2 gap-3">
        {GAMES.map((game) => (
          <li key={game.href}>
            <Link
              href={game.href}
              className="border-trait bg-carte rounded-card flex min-h-24 flex-col items-start justify-center gap-2 border p-4"
            >
              <span aria-hidden className="text-hibiscus">
                {game.icon}
              </span>
              <span className="font-bold">{t(game.key as "quiz")}</span>
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

type Redeemed = Schemas["GlowRedeemed"];

/** « My points »: balance, level, streak, the games, rewards, referral, history. */
export function MyPoints() {
  const t = useTranslations("games.points");
  const tAction = useTranslations("games.actions");
  const tLevel = useTranslations("games.levels");
  const locale = useLocale();
  const toast = useToast();
  const client = useQueryClient();
  const me = useQuery({ queryKey: ["glow-me"], queryFn: getGlowMe });
  const rewards = useQuery({ queryKey: ["glow-rewards"], queryFn: getRewards });
  const vouchers = useQuery({ queryKey: ["glow-vouchers"], queryFn: getVouchers });
  const history = useQuery({ queryKey: ["glow-history"], queryFn: getHistory });
  const [busy, setBusy] = useState<string | null>(null);
  const [done, setDone] = useState<Redeemed | null>(null);

  if (me.isPending) return <Skeleton className="rounded-card h-96" />;
  if (!me.data) {
    return (
      <p role="alert" className="font-bold">
        {me.error instanceof ApiError ? me.error.message : t("error")}
      </p>
    );
  }
  const glow = me.data;
  const number = (value: number) => new Intl.NumberFormat(locale).format(value);
  const date = (iso: string) =>
    new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(new Date(iso));
  const link =
    typeof window === "undefined"
      ? glow.referral.path
      : `${window.location.origin}/${locale}${glow.referral.path}`;
  const inviteText = t("referral.message", { link, points: glow.referral.referee_points });

  const redeem = async (reward: GlowReward) => {
    setBusy(reward.id);
    try {
      const result = await redeemReward(reward.id);
      setDone(result);
      await Promise.all(
        ["glow-me", "glow-rewards", "glow-vouchers", "glow-history"].map((key) =>
          client.invalidateQueries({ queryKey: [key] }),
        ),
      );
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
    } finally {
      setBusy(null);
    }
  };
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(link);
      toast(t("referral.copied"), "success");
    } catch {
      toast(link, "info");
    }
  };
  const rewardButton = (reward: GlowReward) => {
    if (reward.sold_out) return t("rewards.soldOut");
    if (reward.locked) return t("rewards.locked", { level: tLevel(reward.min_level) });
    return t("rewards.exchange", { points: number(reward.cost_points) });
  };

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-center gap-2">
        <h1 className="text-headline flex-1 font-bold">{t("title")}</h1>
        <SpeakButton text={t("speak", { points: glow.balance, days: glow.streak.streak })} />
      </div>

      <section
        aria-labelledby="balance-title"
        className="bg-poudre rounded-card flex flex-col gap-4 p-5"
      >
        <h2 id="balance-title" className="sr-only">
          {t("balanceTitle")}
        </h2>
        <div className="flex items-end justify-between gap-3">
          <p className="flex flex-col">
            <span className="font-display text-display font-black">{number(glow.balance)}</span>
            <span className="font-bold">{t("unit")}</span>
          </p>
          <LevelBadge level={glow.level} />
        </div>
        {glow.next_level && glow.next_level_at ? (
          <Progress
            value={glow.earned_total}
            max={glow.next_level_at}
            label={t("toNext", {
              points: number(glow.next_level_at - glow.earned_total),
              level: tLevel(glow.next_level),
            })}
          />
        ) : (
          <p className="text-small font-bold">{t("top")}</p>
        )}
        {glow.multiplier > 1 && (
          <p className="text-small">
            {t("perk", {
              level: tLevel(glow.level),
              percent: Math.round((glow.multiplier - 1) * 100),
            })}
          </p>
        )}
      </section>

      <section
        aria-labelledby="streak-title"
        className="border-trait bg-carte rounded-card flex flex-col gap-3 border p-5"
      >
        <div className="flex items-center gap-3">
          <Flame streak={glow.streak.streak} bare className="text-headline" />
          <h2 id="streak-title" className="text-title font-bold">
            {glow.streak.streak > 0
              ? t("streak.days", { count: glow.streak.streak })
              : t("streak.none")}
          </h2>
        </div>
        <ol className="flex gap-2" aria-label={t("streak.week")}>
          {Array.from({ length: glow.streak.bonus_every }, (_, index) => {
            const every = glow.streak.bonus_every;
            const litCount = glow.streak.streak === 0 ? 0 : ((glow.streak.streak - 1) % every) + 1;
            const lit = index < litCount;
            return (
              <li
                key={index}
                className={
                  lit
                    ? "bg-hibiscus size-8 rounded-full"
                    : "border-trait bg-lait size-8 rounded-full border-2"
                }
              >
                <span className="sr-only">
                  {t(lit ? "streak.lit" : "streak.dark", { day: index + 1 })}
                </span>
              </li>
            );
          })}
        </ol>
        <p className="text-small text-prune-doux">
          {t("streak.toBonus", {
            count: glow.streak.to_bonus,
            points: glow.scale.find((row) => row.action === "streak")?.points ?? 0,
          })}
        </p>
      </section>

      <section aria-labelledby="games-title" className="flex flex-col gap-3">
        <h2 id="games-title" className="text-title font-bold">
          {t("gamesTitle")}
        </h2>
        <GamesGrid />
      </section>

      <section aria-labelledby="rewards-title" className="flex flex-col gap-3">
        <h2 id="rewards-title" className="text-title font-bold">
          {t("rewards.title")}
        </h2>
        <p className="text-small text-prune-doux">{t("rewards.help")}</p>
        {rewards.isPending && <Skeleton className="rounded-card h-32" />}
        {rewards.data?.length === 0 && <p>{t("rewards.none")}</p>}
        <ul className="flex flex-col gap-3">
          {rewards.data?.map((reward) => (
            <li
              key={reward.id}
              className="border-trait bg-carte rounded-card flex flex-col gap-3 border p-4"
            >
              <div className="flex items-start gap-3">
                <Ticket aria-hidden size={28} weight="duotone" className="text-hibiscus shrink-0" />
                <div className="flex min-w-0 flex-1 flex-col">
                  <span className="font-bold">{reward.title}</span>
                  {reward.description && (
                    <span className="text-small text-prune-doux">{reward.description}</span>
                  )}
                </div>
              </div>
              <Button
                variant={reward.affordable && !reward.locked ? "primary" : "secondary"}
                disabled={!reward.affordable || reward.locked || reward.sold_out || busy !== null}
                onClick={() => redeem(reward)}
                fullWidth
              >
                {rewardButton(reward)}
              </Button>
            </li>
          ))}
        </ul>
      </section>

      {vouchers.data && vouchers.data.length > 0 && (
        <section aria-labelledby="vouchers-title" className="flex flex-col gap-3">
          <h2 id="vouchers-title" className="text-title font-bold">
            {t("vouchers.title")}
          </h2>
          <ul className="flex flex-col gap-2">
            {vouchers.data.map((voucher) => (
              <li
                key={voucher.id}
                className="border-or bg-carte rounded-card flex flex-col gap-1 border-2 border-dashed p-4"
              >
                <span className="font-bold">{voucher.label}</span>
                <span className="text-lead font-bold tracking-widest">{voucher.code}</span>
                <span className="text-small text-prune-doux">
                  {voucher.used_at
                    ? t("vouchers.used", { date: date(voucher.used_at) })
                    : t("vouchers.until", { date: date(voucher.expires_at) })}
                </span>
              </li>
            ))}
          </ul>
          <Link href="/selection" className={buttonClasses({ variant: "secondary" })}>
            {t("vouchers.use")}
          </Link>
        </section>
      )}

      <section
        aria-labelledby="referral-title"
        className="bg-poudre rounded-card flex flex-col gap-3 p-5"
      >
        <h2 id="referral-title" className="text-title font-bold">
          {t("referral.title")}
        </h2>
        <p>
          {t("referral.help", {
            friend: glow.referral.referee_points,
            you: glow.referral.referrer_points,
          })}
        </p>
        <p className="bg-carte text-small rounded-field p-3 font-bold break-all">{link}</p>
        <div className="flex flex-col gap-2">
          <a
            href={`https://wa.me/?text=${encodeURIComponent(inviteText)}`}
            target="_blank"
            rel="noopener noreferrer"
            className={buttonClasses({ fullWidth: true })}
          >
            <WhatsappLogo aria-hidden size={22} weight="bold" />
            {t("referral.whatsapp")}
          </a>
          <Button variant="secondary" fullWidth onClick={copy}>
            <Copy aria-hidden size={22} weight="bold" />
            {t("referral.copy")}
          </Button>
        </div>
        {glow.referral.invited > 0 && (
          <p className="text-small">
            {t("referral.stats", {
              invited: glow.referral.invited,
              rewarded: glow.referral.rewarded,
            })}
          </p>
        )}
      </section>

      <section aria-labelledby="scale-title" className="flex flex-col gap-3">
        <h2 id="scale-title" className="text-title font-bold">
          {t("scale.title")}
        </h2>
        <ul className="border-trait bg-carte rounded-card divide-trait flex flex-col divide-y border">
          {glow.scale.map((row) => (
            <li key={row.action} className="flex items-center gap-3 p-4">
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="font-bold">{tAction(row.action)}</span>
                {row.per_day != null && (
                  <span className="text-small text-prune-doux">
                    {t("scale.perDay", { count: row.per_day })}
                  </span>
                )}
              </span>
              <span className="text-feuille font-bold">+{number(row.points)}</span>
            </li>
          ))}
        </ul>
        <p className="text-small text-prune-doux">
          {t("scale.ceiling", { points: number(glow.daily_max), today: number(glow.earned_today) })}
        </p>
      </section>

      <section aria-labelledby="history-title" className="flex flex-col gap-3">
        <h2 id="history-title" className="text-title font-bold">
          {t("history.title")}
        </h2>
        {history.data?.length === 0 && <p>{t("history.none")}</p>}
        <ul className="flex flex-col gap-2">
          {history.data?.slice(0, 30).map((entry) => (
            <li key={entry.id} className="flex items-center gap-3">
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="font-bold">{entry.note || tAction(entry.action)}</span>
                <span className="text-small text-prune-doux">{date(entry.created_at)}</span>
              </span>
              <span className={entry.amount > 0 ? "text-feuille font-bold" : "font-bold"}>
                {entry.amount > 0 ? `+${number(entry.amount)}` : number(entry.amount)}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <Sheet
        open={done !== null}
        onOpenChange={(open) => !open && setDone(null)}
        title={t("redeemed.title")}
      >
        {done && (
          <div className="flex flex-col items-center gap-4 text-center">
            <Bloom label={t("redeemed.title")} />
            {done.voucher && (
              <>
                <p className="font-bold">{done.voucher.label}</p>
                <p className="font-display text-headline font-black tracking-widest">
                  {done.voucher.code}
                </p>
                <p className="text-small text-prune-doux">
                  {done.voucher.amount_off_minor > 0
                    ? t("redeemed.amount", {
                        amount: formatMoney(done.voucher.amount_off_minor, "XOF", locale),
                      })
                    : t("redeemed.express")}
                </p>
                <Link href="/selection" className={buttonClasses({ fullWidth: true })}>
                  {t("vouchers.use")}
                </Link>
              </>
            )}
            {done.course && (
              <Link
                href={`/academie/${done.course.slug}`}
                className={buttonClasses({ fullWidth: true })}
              >
                {t("redeemed.course", { title: done.course.title })}
              </Link>
            )}
          </div>
        )}
      </Sheet>
    </div>
  );
}
