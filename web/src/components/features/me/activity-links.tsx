"use client";

import {
  AirplaneTilt,
  BookmarkSimple,
  CalendarCheck,
  CalendarDots,
  CaretRight,
  Heart,
  Images,
  Package,
  Receipt,
  ShoppingBag,
  Star,
  Storefront,
  UsersThree,
  Wallet,
} from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { Link } from "@/lib/i18n/navigation";

const LINKS: { href: string; key: string; icon: ReactNode }[] = [
  {
    href: "/appointments",
    key: "appointments",
    icon: <CalendarCheck size={28} weight="duotone" />,
  },
  { href: "/cart", key: "cart", icon: <ShoppingBag size={28} weight="duotone" /> },
  { href: "/orders", key: "orders", icon: <Package size={28} weight="duotone" /> },
  { href: "/wishlist", key: "wishlist", icon: <Heart size={28} weight="duotone" /> },
  {
    href: "/selection/orders",
    key: "selection",
    icon: <AirplaneTilt size={28} weight="duotone" />,
  },
  { href: "/me/posts", key: "posts", icon: <Images size={28} weight="duotone" /> },
  { href: "/saved", key: "saved", icon: <BookmarkSimple size={28} weight="duotone" /> },
  { href: "/following", key: "following", icon: <UsersThree size={28} weight="duotone" /> },
  { href: "/me/reviews", key: "reviews", icon: <Star size={28} weight="duotone" /> },
  { href: "/payments", key: "payments", icon: <Receipt size={28} weight="duotone" /> },
  { href: "/pro/agenda", key: "agenda", icon: <CalendarDots size={28} weight="duotone" /> },
  { href: "/pro/salon", key: "salon", icon: <Storefront size={28} weight="duotone" /> },
  { href: "/pro/wallet", key: "wallet", icon: <Wallet size={28} weight="duotone" /> },
  { href: "/pro/shop", key: "myShop", icon: <Storefront size={28} weight="duotone" /> },
];

/** Her activity on Solange Glow: posts, saved posts, people followed, reviews to leave. */
export function ActivityLinks() {
  const t = useTranslations("social.activity");
  return (
    <section aria-labelledby="activity-title" className="flex flex-col gap-3">
      <h2 id="activity-title" className="text-title font-bold">
        {t("title")}
      </h2>
      <ul className="flex flex-col gap-2">
        {LINKS.map((link) => (
          <li key={link.href}>
            <Link
              href={link.href}
              className="border-trait bg-carte rounded-card flex min-h-16 items-center gap-4 border p-4"
            >
              <span aria-hidden className="text-hibiscus">
                {link.icon}
              </span>
              <span className="flex-1 font-bold">{t(link.key as "posts")}</span>
              <CaretRight aria-hidden size={20} />
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
