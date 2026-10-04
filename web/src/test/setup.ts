import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

/** One shared router, so tests can check where the app navigated. */
const routerMock = vi.hoisted(() => ({
  push: vi.fn(),
  replace: vi.fn(),
  prefetch: vi.fn(),
  back: vi.fn(),
  refresh: vi.fn(),
}));

// next-intl navigation relies on the Next.js router, absent in unit tests.
vi.mock("next/navigation", () => ({
  usePathname: () => "/fr/explore",
  useRouter: () => routerMock,
  useParams: () => ({ locale: "fr" }),
  useSearchParams: () => new URLSearchParams(),
  redirect: vi.fn(),
  notFound: vi.fn(),
  permanentRedirect: vi.fn(),
}));

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
  document.cookie = "sg_signed_in=; max-age=0; path=/";
  Object.values(routerMock).forEach((fn) => fn.mockReset());
  vi.unstubAllGlobals();
});
