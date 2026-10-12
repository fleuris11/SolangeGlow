"use client";

import { Compass, UserMinus } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";

import { Avatar } from "@/components/ui/avatar";
import { Button, buttonClasses } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { follow, getFollowing } from "@/lib/api/social";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";

/** The people she follows; an empty list invites to discover pros nearby. */
export function FollowingList() {
  const t = useTranslations("social.following");
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["following"], queryFn: getFollowing });

  if (query.isPending) return <Skeleton className="rounded-card h-48" />;
  const people = query.data ?? [];
  if (people.length === 0) {
    return (
      <EmptyState
        icon={<Compass size={48} weight="duotone" />}
        title={t("emptyTitle")}
        description={t("emptyText")}
        action={
          <Link href="/explore" className={buttonClasses({ size: "lg" })}>
            {t("emptyCta")}
          </Link>
        }
      />
    );
  }
  return (
    <ul className="flex flex-col gap-2">
      {people.map((person) => {
        const face = (
          <>
            <Avatar
              name={person.name}
              src={mediaSrc(person.photo, "thumb")}
              size="md"
              halo={person.has_story}
            />
            <span className="flex min-w-0 flex-col">
              <span className="truncate font-bold">{person.name}</span>
              <span className="text-small text-prune-doux">
                {t("posts", { count: person.post_count })}
              </span>
            </span>
          </>
        );
        return (
          <li
            key={person.id}
            className="border-trait bg-carte rounded-card flex items-center gap-3 border p-3"
          >
            {person.pro_slug ? (
              <Link href={`/${person.pro_slug}`} className="flex min-w-0 flex-1 items-center gap-3">
                {face}
              </Link>
            ) : (
              <span className="flex min-w-0 flex-1 items-center gap-3">{face}</span>
            )}
            <Button
              variant="quiet"
              onClick={async () => {
                await follow(person.id, false);
                await queryClient.invalidateQueries({ queryKey: ["following"] });
              }}
            >
              <UserMinus aria-hidden size={20} />
              {t("unfollow")}
            </Button>
          </li>
        );
      })}
    </ul>
  );
}
