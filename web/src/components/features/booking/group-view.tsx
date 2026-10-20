"use client";

import { CheckCircle, Circle, ShareNetwork, UsersThree } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState, useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { ApiError, hasSession } from "@/lib/api/client";
import { getGroup, payGroupShare } from "@/lib/api/booking";
import { rememberReturnPath } from "@/lib/auth/return-path";
import { dayName, localDay, timeAt } from "@/lib/booking/time";
import { usePathname, useRouter } from "@/lib/i18n/navigation";
import { formatMoney } from "@/lib/money";

const subscribeNothing = () => () => {};

/** A group booking: each place, who paid, and « Pay my share ». */
export function GroupView({ token }: { token: string }) {
  const t = useTranslations("booking.group");
  const tFlow = useTranslations("booking.flow");
  const locale = useLocale();
  const toast = useToast();
  const router = useRouter();
  const pathname = usePathname();
  const signedIn = useSyncExternalStore(subscribeNothing, hasSession, () => false);
  const query = useQuery({
    queryKey: ["group", token],
    queryFn: () => getGroup(token),
    retry: false,
  });
  const [busy, setBusy] = useState(false);

  if (query.isPending) return <Skeleton className="rounded-card h-80" />;
  if (!query.data) {
    return <EmptyState icon={<UsersThree size={44} weight="duotone" />} title={t("notFound")} />;
  }
  const group = query.data;
  const zone = group.pro.timezone;
  const unpaid = group.places.filter((p) => !p.paid);
  const mine = group.places.find((p) => p.mine && !p.paid);
  const free = group.places.find((p) => !p.taken && !p.paid);
  const canPay = group.status === "collecting" && (mine || free || group.is_organizer);

  const pay = async () => {
    if (!signedIn) {
      rememberReturnPath(pathname);
      router.push("/auth?as=client");
      return;
    }
    setBusy(true);
    try {
      const answer = await payGroupShare(token, mine?.id ?? free?.id);
      window.location.assign(answer.checkout_url);
    } catch (caught) {
      toast(caught instanceof ApiError ? caught.message : t("error"), "warning");
      setBusy(false);
    }
  };

  const share = async () => {
    const url = `${window.location.origin}/${locale}${group.share_url}`;
    const data = {
      title: group.title || group.service_name,
      text: t("shareText", { name: group.organizer_name }),
      url,
    };
    if (navigator.share) {
      try {
        await navigator.share(data);
      } catch {
        // Closed by the person.
      }
      return;
    }
    await navigator.clipboard?.writeText(url);
    toast(t("copied"), "success");
  };

  const title = group.title || t("title", { name: group.organizer_name });
  return (
    <article className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <UsersThree aria-hidden size={30} weight="duotone" className="text-hibiscus" />
          <h1 className="text-headline flex-1 font-bold">{title}</h1>
          <SpeakButton text={title} />
        </div>
        <p className="font-bold">
          {group.service_name}, {group.pro.name}
        </p>
        <p className="text-prune-doux">{t(`status.${group.status as "collecting"}`)}</p>
      </header>
      <ol className="flex flex-col gap-2" aria-label={t("places")}>
        {group.places.map((place, i) => (
          <li
            key={place.id}
            className="border-trait rounded-card flex min-h-16 items-center gap-3 border p-3"
          >
            {place.paid ? (
              <CheckCircle aria-hidden size={26} weight="fill" className="text-feuille" />
            ) : (
              <Circle aria-hidden size={26} className="text-prune-doux" />
            )}
            <span className="flex flex-1 flex-col">
              <span className="font-bold">{t("place", { number: i + 1 })}</span>
              <span className="text-small text-prune-doux">
                {tFlow("when", {
                  day: dayName(localDay(place.starts_at, zone), locale),
                  time: timeAt(place.starts_at, zone, locale),
                })}
              </span>
            </span>
            <span className="text-small font-bold">
              {place.paid
                ? t("paid")
                : place.mine
                  ? t("yours")
                  : place.taken
                    ? t("taken")
                    : t("free")}
            </span>
          </li>
        ))}
      </ol>
      {group.share_minor > 0 && group.status === "collecting" && (
        <p className="text-prune-doux">
          {t("shareAmount", {
            amount: formatMoney(group.share_minor, group.currency || "XOF", locale),
            count: unpaid.length,
          })}
        </p>
      )}
      {canPay && group.share_minor > 0 && (
        <Button size="lg" fullWidth disabled={busy} onClick={() => void pay()}>
          {mine || free
            ? t("payMine", {
                amount: formatMoney(group.share_minor, group.currency || "XOF", locale),
              })
            : t("payRest", {
                amount: formatMoney(group.share_minor, group.currency || "XOF", locale),
              })}
        </Button>
      )}
      <Button variant="secondary" fullWidth onClick={() => void share()}>
        <ShareNetwork aria-hidden size={24} />
        {t("share")}
      </Button>
    </article>
  );
}
