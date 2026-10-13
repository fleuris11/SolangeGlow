import { getMedia, uploadPaymentPicture } from "@/lib/api/payments";

/** Sends a picture and waits until it is prepared; returns its id, or throws. */
export async function sendPicture(
  file: Blob,
  purpose: "delivery_proof" | "dispute_evidence",
): Promise<string> {
  const sent = await uploadPaymentPicture(file, purpose);
  for (let attempt = 0; attempt < 40; attempt++) {
    const media = await getMedia(sent.id);
    if (media.status === "ready") return media.id;
    if (media.status === "rejected" || media.status === "failed") {
      throw new Error(media.error || "refused");
    }
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
  throw new Error("timeout");
}
