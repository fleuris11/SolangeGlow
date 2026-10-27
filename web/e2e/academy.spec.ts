import path from "node:path";

import { expect, test, type Page } from "@playwright/test";

import {
  expectNoSeriousA11yIssue,
  openWith,
  signInAsNewClient,
  signInWithPhone,
  VIEWPORTS,
} from "./helpers";

/**
 * Academy (module 7) with the demo data: the free course of the platform that gives the badge
 * (« Hygiène et sécurité au salon », with quizzes), the paid course of Institut Prisca,
 * a live of the platform. Institut Prisca (+2290197000108) writes a new course.
 */
const TRAINER_PHONE = "+2290197000108";
const LOOK = { theme: "light", textSize: "normal" } as const;
const API = { "X-SG-Client": "web" };
const FREE_COURSE = "hygiene-et-securite-au-salon";
const PAID_COURSE = "maquillage-mariee-en-5-etapes";

async function json<T>(response: Awaited<ReturnType<Page["request"]["get"]>>): Promise<T> {
  expect(response.ok(), await response.text()).toBe(true);
  return (await response.json()) as T;
}

type Detail = {
  modules: { id: string; lessons: { id: string }[]; questions_count: number }[];
};

test("a student follows a free course to its certificate, offline lesson included", async ({
  browser,
}) => {
  test.setTimeout(480_000);
  const context = await browser.newContext({ viewport: VIEWPORTS.mobile });
  const student = await context.newPage();

  // --- The catalogue, rendered on the server -------------------------------------------------
  await openWith(student, "/fr/academie", LOOK);
  await expect(student.getByRole("heading", { name: "Académie", level: 1 })).toBeVisible({
    timeout: 90_000,
  });
  await expect(student.getByRole("link", { name: /Hygiène et sécurité au salon/ })).toBeVisible();
  await expectNoSeriousA11yIssue(student);
  await student.screenshot({ path: "e2e/screenshots/academy-catalogue.png", fullPage: true });

  // --- The course page, then signed in: start for free --------------------------------------
  await signInAsNewClient(student, "Awa");
  await openWith(student, `/fr/academie/${FREE_COURSE}`, LOOK);
  await expect(
    student.getByRole("heading", { name: "Hygiène et sécurité au salon", level: 1 }),
  ).toBeVisible({ timeout: 90_000 });
  await expectNoSeriousA11yIssue(student);
  await student.screenshot({ path: "e2e/screenshots/academy-course.png", fullPage: true });
  await student.getByRole("button", { name: "Commencer gratuitement" }).click();

  // --- The player: low quality in data saver, a lesson kept for offline ---------------------
  await expect(student.locator("video")).toBeVisible({ timeout: 90_000 });
  await expect(student.getByRole("radio", { name: "Économie" })).toBeAttached();
  await expectNoSeriousA11yIssue(student);
  await student.screenshot({ path: "e2e/screenshots/academy-player.png", fullPage: true });
  await student.getByRole("button", { name: "Télécharger pour regarder sans réseau" }).click();
  await expect(student.getByText("Leçon gardée sur ton téléphone.")).toBeVisible({
    timeout: 120_000,
  });
  await context.setOffline(true);
  await expect(student.getByText(/Pas de réseau : tu regardes la copie/).first()).toBeVisible();
  await context.setOffline(false);

  // --- Every lesson watched (the player saves the end), then the quizzes ---------------------
  const detail = await json<Detail>(
    await student.request.get(`/api/v1/academy/courses/${FREE_COURSE}`),
  );
  for (const chapter of detail.modules) {
    for (const lesson of chapter.lessons) {
      await json(
        await student.request.post(`/api/v1/academy/lessons/${lesson.id}/position`, {
          data: { seconds: 185, ended: true },
          headers: API,
        }),
      );
    }
  }
  for (const [index, chapter] of detail.modules.entries()) {
    await openWith(student, `/fr/academie/${FREE_COURSE}/quiz/${chapter.id}`, LOOK);
    await expect(student.getByRole("button", { name: "Valider mes réponses" })).toBeVisible({
      timeout: 90_000,
    });
    // Demo answers: 48 hours, after every client.
    await student.getByRole("radio", { name: "48 heures" }).click();
    await student.getByRole("radio", { name: "Après chaque cliente" }).click();
    if (index === 0) await expectNoSeriousA11yIssue(student);
    await student.getByRole("button", { name: "Valider mes réponses" }).click();
    await expect(student.getByText(/Réussi : 100 %/)).toBeVisible();
    if (index === 0) {
      await student.screenshot({ path: "e2e/screenshots/academy-quiz.png", fullPage: true });
    }
  }

  // --- My courses: the certificate, and its public check page --------------------------------
  await openWith(student, "/fr/academie/mes-formations", LOOK);
  const pdf = student.getByRole("link", { name: "Mon certificat (PDF)" });
  await expect(pdf).toBeVisible({ timeout: 90_000 });
  await expectNoSeriousA11yIssue(student);
  await student.screenshot({ path: "e2e/screenshots/academy-mine.png", fullPage: true });
  const pdfAnswer = await student.request.get((await pdf.getAttribute("href")) as string);
  expect(pdfAnswer.headers()["content-type"]).toBe("application/pdf");
  await student.getByRole("link", { name: "Page de vérification" }).click();
  await expect(student.getByRole("heading", { name: "Certificat valable" })).toBeVisible({
    timeout: 90_000,
  });
  await expectNoSeriousA11yIssue(student);
  await student.screenshot({ path: "e2e/screenshots/academy-certificate.png", fullPage: true });

  // --- A paid course: the waiver, then the test payment --------------------------------------
  await openWith(student, `/fr/academie/${PAID_COURSE}`, LOOK);
  await student.getByRole("button", { name: /Acheter pour 5\s000 FCFA/ }).click();
  const pay = student.getByRole("button", { name: /Payer 5\s000 FCFA/ });
  await expect(pay).toBeDisabled();
  await student.getByRole("checkbox", { name: /Je renonce à mon droit/ }).check();
  await expectNoSeriousA11yIssue(student);
  await pay.click();
  await expect(student.getByText(/aucun argent réel ne bouge/)).toBeVisible({ timeout: 60_000 });
  await student.getByRole("button", { name: /Paiement réussi/ }).click();
  await expect
    .poll(
      async () => {
        const course = await json<{ enrollment: { status: string } | null }>(
          await student.request.get(`/api/v1/academy/courses/${PAID_COURSE}`),
        );
        return course.enrollment?.status;
      },
      { timeout: 60_000 },
    )
    .toBe("active");

  // --- A live: registration and the waiting room ----------------------------------------------
  await openWith(student, "/fr/academie/lives", LOOK);
  await student.getByRole("link", { name: "Voir le live" }).first().click();
  await student.getByRole("button", { name: "M'inscrire" }).click();
  await expect(student.getByText("La salle ouvre quelques minutes avant le début.")).toBeVisible({
    timeout: 30_000,
  });
  await expectNoSeriousA11yIssue(student);
  await student.screenshot({ path: "e2e/screenshots/academy-live.png", fullPage: true });
  await context.close();
});

test("a pro writes a course step by step and sends it to the team", async ({ browser }) => {
  test.setTimeout(480_000);
  const context = await browser.newContext({ viewport: VIEWPORTS.mobile });
  const pro = await context.newPage();
  await signInWithPhone(pro, TRAINER_PHONE);

  await openWith(pro, "/fr/pro/academy", LOOK);
  await expect(pro.getByRole("heading", { name: "Espace formatrice" })).toBeVisible({
    timeout: 90_000,
  });
  await expectNoSeriousA11yIssue(pro);
  await pro.screenshot({ path: "e2e/screenshots/academy-studio.png", fullPage: true });

  // 1. About.
  await pro.getByRole("button", { name: "Créer une formation" }).click();
  await pro.getByLabel("Titre de la formation").fill(`Tresses collées ${Date.now() % 10_000}`);
  await pro.getByRole("button", { name: "Créer et continuer" }).click();
  await expect(pro.getByRole("heading", { name: "Présentation" })).toBeVisible({ timeout: 90_000 });
  await pro.getByLabel("En une phrase").fill("Des raies nettes et régulières.");
  await pro.getByRole("radio", { name: "Débutante" }).check();
  await expectNoSeriousA11yIssue(pro);
  await pro.screenshot({ path: "e2e/screenshots/academy-editor.png", fullPage: true });
  await pro.getByRole("button", { name: "Enregistrer et continuer" }).click();

  // 2. A module and a lesson with its video (3 minutes, processed by the worker).
  await expect(pro.getByRole("heading", { name: "Les leçons" })).toBeVisible();
  await pro.getByLabel("Nouveau module").fill("Les raies");
  await pro.getByRole("button", { name: "Ajouter le module" }).click();
  await pro.getByLabel("Titre de la leçon").fill("Tracer une raie droite");
  await pro
    .locator('input[type="file"][accept="video/*"]')
    .first()
    .setInputFiles(path.resolve("e2e/fixtures/lesson.mp4"));
  await expect(pro.getByText("Vidéo envoyée : elle se prépare.")).toBeVisible({ timeout: 60_000 });
  await pro.getByRole("button", { name: "Enregistrer la leçon" }).click();
  await expect(pro.getByText("Vidéo prête")).toBeVisible({ timeout: 180_000 });
  await pro.getByRole("button", { name: "Continuer", exact: true }).click();

  // 3. A question.
  await expect(pro.getByRole("heading", { name: "Les quiz" })).toBeVisible();
  await pro.getByRole("textbox", { name: "Question" }).fill("On tire fort sur les cheveux ?");
  await pro.getByRole("textbox", { name: "Réponse 1" }).fill("Oui");
  await pro.getByRole("textbox", { name: "Réponse 2" }).fill("Non, sans tirer");
  await pro.getByRole("radio", { name: "La réponse 2 est la bonne" }).check();
  await pro.getByRole("button", { name: "Ajouter la question" }).click();
  await expect(pro.getByText("Bonne réponse : Non, sans tirer")).toBeVisible();
  await pro.getByRole("button", { name: "Continuer", exact: true }).click();

  // 4. Price, 5. send.
  await pro.getByRole("radio", { name: "À l'unité" }).check();
  await pro.getByLabel(/Prix \(FCFA\)/).fill("3000");
  await pro.getByRole("button", { name: "Enregistrer et continuer" }).click();
  await expect(pro.getByRole("heading", { name: "Envoyer" })).toBeVisible();
  await pro.getByRole("button", { name: "Envoyer à l'équipe" }).click();
  await expect(pro.getByText(/En vérification par l'équipe/)).toBeVisible({ timeout: 30_000 });
  await expectNoSeriousA11yIssue(pro);
  await context.close();
});
