import type { ProductDetail } from "@/lib/api/shop";
import { currencyExponent } from "@/lib/money";

function major(amountMinor: number, currency: string): string {
  return (amountMinor / 10 ** currencyExponent(currency)).toFixed(currencyExponent(currency));
}

/** schema.org Product: name, pictures, price, stock and the shop that sells it. */
export function productJsonLd(product: ProductDetail, url: string, images: string[]) {
  return {
    "@context": "https://schema.org",
    "@type": "Product",
    name: product.title,
    description: product.description || undefined,
    image: images.length ? images : undefined,
    category: product.category?.name,
    brand: { "@type": "Brand", name: product.shop.name },
    offers: {
      "@type": "Offer",
      url,
      priceCurrency: product.currency,
      price: major(product.price_minor, product.currency),
      availability: product.in_stock
        ? "https://schema.org/InStock"
        : "https://schema.org/OutOfStock",
      seller: { "@type": "Organization", name: product.shop.name },
    },
  };
}
