"use client"

import { useEffect, useState } from "react"
import { categoryPhotoUrl, fallbackUrl, garmentPhotoUrl, pickPhoto, pixabayPhotoUrl, type Item } from "./photos"

export default function ProductImg({ item, alt, height = 340, src }: { item: Item; alt: string; height?: number; src?: string }) {
  // src (when given) is the grid's deduped pick — no repeats on the page.
  // The rest of the chain is per-image fallback if a URL ever breaks.
  const first = src || pickPhoto(item)
  const steps = [first, pixabayPhotoUrl(item), garmentPhotoUrl(item), categoryPhotoUrl(item), fallbackUrl(item)].filter((u, i, a) => u && a.indexOf(u) === i)
  const [step, setStep] = useState(0)
  useEffect(() => setStep(0), [item.article_id, first])
  return (
    <img
      src={steps[Math.min(step, steps.length - 1)]}
      alt={alt}
      loading="lazy"
      referrerPolicy="no-referrer"
      onError={() => setStep((s) => Math.min(s + 1, steps.length - 1))}
      style={{ width: "100%", height, objectFit: "cover", background: "#ece7dd", display: "block" }}
    />
  )
}
