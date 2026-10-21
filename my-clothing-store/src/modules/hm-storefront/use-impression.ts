"use client"

import { useEffect, useRef } from "react"
import type { Item, RecoResult } from "./photos"
import { sendEvent } from "./photos"

export function useImpression(item: Item, result: RecoResult | null) {
  const ref = useRef<HTMLElement>(null)
  const sentKey = useRef<string | null>(null)

  useEffect(() => {
    const node = ref.current
    if (!node || !result || typeof IntersectionObserver === "undefined") return

    const key = `${result.request_id}:${result.variant}:${item.article_id}`
    if (sentKey.current === key) return

    const observer = new IntersectionObserver(([entry]) => {
      if (!entry?.isIntersecting || entry.intersectionRatio < 0.5) return

      sentKey.current = key
      void sendEvent("impression", item, result)
      observer.disconnect()
    }, { threshold: [0.5] })

    observer.observe(node)
    return () => observer.disconnect()
  }, [item, result])

  return ref
}
