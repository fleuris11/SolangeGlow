import { useTranslations } from "next-intl";

import { TITLE } from "@/components/features/marketing/chrome";
import { EditorialSection } from "@/components/ui/editorial-section";
import { Link } from "@/lib/i18n/navigation";

const QUESTIONS = ["account", "free", "signup", "pro", "qr", "payment", "france"] as const;

/** The answer is the large type. Plain radio buttons: arrows and tab work, no script. */
export function QuestionIndex() {
  const t = useTranslations("marketing.questions");
  return (
    <EditorialSection
      aria-labelledby="questions-title"
      className="px-4 py-16 md:px-8 xl:px-10 xl:py-24"
    >
      <h2 id="questions-title" className={`${TITLE} text-headline xl:text-display`}>
        {t("title")}
      </h2>
      <div className="sg-index mt-8 grid gap-x-16 gap-y-1">
        {QUESTIONS.map((key, index) => (
          <div key={key}>
            <input
              type="radio"
              name="home-question"
              id={`question-${key}`}
              defaultChecked={index === 0}
              className="sr-only"
            />
            <label
              htmlFor={`question-${key}`}
              className="text-prune-doux flex min-h-12 cursor-pointer items-center gap-3 py-1 font-semibold"
            >
              <span aria-hidden className="sg-dot bg-prune-doux size-2 shrink-0 rounded-full" />
              {t(`${key}.q`)}
            </label>
            <p className="sg-answer max-xl:text-lead xl:text-title pb-4 pl-5 xl:pb-0 xl:pl-0">
              {t(`${key}.a`)}
            </p>
          </div>
        ))}
      </div>
      <Link
        href="/aide"
        className="mt-6 inline-flex min-h-12 items-center font-semibold underline underline-offset-4"
      >
        {t("help")}
      </Link>
    </EditorialSection>
  );
}
