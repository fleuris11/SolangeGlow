import type { Showcase } from "@/lib/api/pros";
import { currencyExponent } from "@/lib/money";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

/** schema.org type from the trades: what Google shows for a local business. */
function businessType(showcase: Showcase): string {
  const keys = showcase.trades.map((trade) => trade.key);
  if (keys.some((key) => key === "hair" || key === "braids")) return "HairSalon";
  if (keys.includes("nails")) return "NailSalon";
  if (keys.some((key) => ["makeup", "skincare", "headwrap"].includes(key))) return "BeautySalon";
  return "LocalBusiness";
}

function socialUrl(network: string, value: string): string | null {
  if (value.startsWith("http")) return value;
  const handle = value.replace(/^@/, "");
  const bases: Record<string, string> = {
    instagram: "https://www.instagram.com/",
    tiktok: "https://www.tiktok.com/@",
    facebook: "https://www.facebook.com/",
    youtube: "https://www.youtube.com/@",
  };
  return bases[network] ? bases[network] + handle : null;
}

function major(amountMinor: number, currency: string): string {
  return (amountMinor / 10 ** currencyExponent(currency)).toFixed(currencyExponent(currency));
}

/**
 * LocalBusiness structured data of a showcase. The exact address and position are given
 * only when the pro receives clients (never for home visits only).
 */
export function localBusinessJsonLd(showcase: Showcase, url: string, image?: string) {
  const place = showcase.place;
  const exact = place.receives_clients && place.latitude !== null && place.longitude !== null;
  const sameAs = Object.entries(showcase.social_links)
    .map(([network, value]) => socialUrl(network, value))
    .filter(Boolean);
  const offers = showcase.services
    .filter((service) => service.price_minor !== null && service.price_kind !== "quote")
    .slice(0, 20)
    .map((service) => ({
      "@type": "Offer",
      itemOffered: { "@type": "Service", name: service.name },
      price: major(service.price_minor ?? 0, service.currency),
      priceCurrency: service.currency,
    }));

  return {
    "@context": "https://schema.org",
    "@type": businessType(showcase),
    name: showcase.business_name,
    url,
    ...(image ? { image } : {}),
    ...(showcase.bio ? { description: showcase.bio } : {}),
    address: {
      "@type": "PostalAddress",
      ...(exact && place.address ? { streetAddress: place.address } : {}),
      addressLocality: place.city,
      ...(place.district ? { addressRegion: place.district } : {}),
      ...(place.country ? { addressCountry: place.country } : {}),
    },
    ...(exact
      ? { geo: { "@type": "GeoCoordinates", latitude: place.latitude, longitude: place.longitude } }
      : {}),
    ...(showcase.hours.length
      ? {
          openingHoursSpecification: showcase.hours.map((period) => ({
            "@type": "OpeningHoursSpecification",
            dayOfWeek: `https://schema.org/${DAYS[period.weekday]}`,
            opens: period.opens_at,
            closes: period.closes_at,
          })),
        }
      : {}),
    ...(showcase.rating_count > 0 && showcase.rating_average !== null
      ? {
          aggregateRating: {
            "@type": "AggregateRating",
            ratingValue: showcase.rating_average,
            reviewCount: showcase.rating_count,
          },
        }
      : {}),
    ...(sameAs.length ? { sameAs } : {}),
    ...(offers.length
      ? {
          hasOfferCatalog: {
            "@type": "OfferCatalog",
            name: showcase.business_name,
            itemListElement: offers,
          },
        }
      : {}),
  };
}

/** Safe to put inside a <script> tag. */
export function jsonLdScript(data: object): string {
  return JSON.stringify(data).replace(/</g, "\\u003c");
}
