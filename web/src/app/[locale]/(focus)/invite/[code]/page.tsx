import { HandHeart } from "@phosphor-icons/react/dist/ssr";
import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { InviteJoin } from "@/components/features/games/invite-join";
import { buttonClasses } from "@/components/ui/button";
import { SpeakButton } from "@/components/ui/speak-button";
import { inviteOnServer } from "@/lib/api/server";
import { Link } from "@/lib/i18n/navigation";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale; code: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "games.titles" });
  return { title: t("invite"), robots: { index: false, follow: false } };
}

/** The personal invitation link of a client: who invites, what the friend gets. */
export default async function InvitePage({ params }: Props) {
  const { locale, code } = await params;
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: "games.invite" });
  const invite = await inviteOnServer(code, locale).catch(() => null);
  if (!invite) {
    return (
      <div className="flex flex-col items-center gap-4 text-center">
        <h1 className="text-headline font-bold">{t("broken")}</h1>
        <Link href="/" className={buttonClasses({ variant: "secondary" })}>
          {t("home")}
        </Link>
      </div>
    );
  }
  const title = invite.name ? t("title", { name: invite.name }) : t("titleNoName");
  return (
    <div className="flex flex-col items-center gap-6 text-center">
      <HandHeart aria-hidden size={72} weight="duotone" className="text-hibiscus" />
      <div className="flex items-start gap-2">
        <h1 className="font-display text-headline font-black">{title}</h1>
        <SpeakButton text={`${title}. ${t("text", { points: invite.points })}`} />
      </div>
      <p className="text-lead">{t("text", { points: invite.points })}</p>
      <ul className="flex flex-col gap-2 text-left">
        <li>{t("why1")}</li>
        <li>{t("why2")}</li>
        <li>{t("why3")}</li>
      </ul>
      <div className="w-full">
        <InviteJoin code={code} />
      </div>
    </div>
  );
}
