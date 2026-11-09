"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { EVERYWHERE, readViewerCountry, writeViewerCountry } from "@/lib/geo/viewer-country";

/**
 * First visit only: the country is found from the time zone of the device (no permission asked),
 * then the page is drawn again for that country. She can change it in the city picker.
 */
export function CountryDetect() {
  const router = useRouter();
  useEffect(() => {
    if (readViewerCountry()) return;
    const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    // Loaded only on this first visit: nothing added to the pages (ADR-004).
    import("@/lib/api/accounts")
      .then(({ getCountries }) => getCountries())
      .then((countries) => {
        const found = countries.find((country) => country.timezone === zone);
        writeViewerCountry(found ? found.code : EVERYWHERE);
        if (found) router.refresh();
      })
      .catch(() => undefined);
  }, [router]);
  return null;
}
