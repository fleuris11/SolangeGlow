"use client";

import { ChatCircleText, Star } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import type { MyPro } from "@/lib/api/pros";
import { getReviews, replyToReview, type Review } from "@/lib/api/social";

import { fieldClass, SectionFrame } from "./section-frame";

function ReplyForm({ review, onDone }: { review: Review; onDone: () => void }) {
  const t = useTranslations("pros.my.reviews");
  const toast = useToast();
  const [text, setText] = useState("");
  const [error, setError] = useState<string>();
  const send = async () => {
    try {
      await replyToReview(review.id, text);
      toast(t("replied"), "success");
      onDone();
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : t("error"));
    }
  };
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={`reply-${review.id}`} className="font-bold">
        {t("yourReply")}
      </label>
      <textarea
        id={`reply-${review.id}`}
        rows={2}
        maxLength={1000}
        value={text}
        onChange={(event) => setText(event.target.value)}
        className={fieldClass}
      />
      <p className="text-small text-prune-doux">{t("once")}</p>
      {error && (
        <p role="alert" className="text-alerte font-bold">
          {error}
        </p>
      )}
      <Button variant="secondary" disabled={!text.trim()} onClick={() => void send()}>
        <ChatCircleText aria-hidden size={22} />
        {t("reply")}
      </Button>
    </div>
  );
}

/** Reviews of her clients; she can reply once to each. */
export function ReviewsPart({ pro }: { pro: MyPro }) {
  const t = useTranslations("pros.my.reviews");
  const locale = useLocale();
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["my-reviews", pro.slug],
    queryFn: () => getReviews(pro.slug),
    enabled: pro.status === "published",
  });

  return (
    <SectionFrame title={t("title")} help={t("help")}>
      {pro.status !== "published" ? (
        <p className="text-prune-doux">{t("publishFirst")}</p>
      ) : query.isPending ? (
        <Skeleton className="rounded-card h-48" />
      ) : !query.data?.results.length ? (
        <p className="text-prune-doux">{t("empty")}</p>
      ) : (
        <ul className="flex flex-col gap-4">
          {query.data.results.map((review) => (
            <li
              key={review.id}
              className="border-trait rounded-card flex flex-col gap-2 border p-4"
            >
              <p className="flex items-center gap-2 font-bold">
                <Star aria-hidden size={20} weight="fill" className="text-or" />
                {t("stars", { count: review.rating })}, {review.author_name}
              </p>
              <p className="text-mention text-prune-doux">
                {new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(
                  new Date(review.created_at),
                )}
              </p>
              {review.text && <p>{review.text}</p>}
              {review.reply ? (
                <p className="bg-poudre rounded-card p-3">{review.reply}</p>
              ) : (
                <ReplyForm
                  review={review}
                  onDone={() =>
                    void queryClient.invalidateQueries({ queryKey: ["my-reviews", pro.slug] })
                  }
                />
              )}
            </li>
          ))}
        </ul>
      )}
    </SectionFrame>
  );
}
