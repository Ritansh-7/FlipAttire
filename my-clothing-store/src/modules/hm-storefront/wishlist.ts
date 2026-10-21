"use client"

import { useEffect, useState } from "react"
import type { Item } from "./photos"

const WISHLIST_KEY = "hm_myntra_wishlist_v1"

export function loadWishlist(): Item[] {
  if (typeof window === "undefined") return []
  try {
    const raw = localStorage.getItem(WISHLIST_KEY)
    return raw ? (JSON.parse(raw) as Item[]) : []
  } catch {
    return []
  }
}

export function saveWishlist(items: Item[]) {
  try {
    localStorage.setItem(WISHLIST_KEY, JSON.stringify(items))
  } catch {
    /* storage full/blocked */
  }
  window.dispatchEvent(new Event("hm:wishlist"))
}

export function toggleWishlistStored(item: Item): boolean {
  const current = loadWishlist()
  const exists = current.some((entry) => entry.article_id === item.article_id)
  let updated: Item[]
  if (exists) {
    updated = current.filter((entry) => entry.article_id !== item.article_id)
  } else {
    updated = [...current, item]
  }
  saveWishlist(updated)
  return !exists
}

export function isWishlistedStored(articleId: string): boolean {
  const current = loadWishlist()
  return current.some((entry) => entry.article_id === articleId)
}

export function useWishlist() {
  const [wishlist, setWishlist] = useState<Item[]>([])
  useEffect(() => {
    setWishlist(loadWishlist())
    const sync = () => setWishlist(loadWishlist())
    window.addEventListener("hm:wishlist", sync)
    window.addEventListener("storage", sync)
    return () => {
      window.removeEventListener("hm:wishlist", sync)
      window.removeEventListener("storage", sync)
    }
  }, [])

  return {
    wishlist,
    toggleWishlist: (item: Item) => toggleWishlistStored(item),
    isWishlisted: (articleId: string) => wishlist.some((item) => item.article_id === articleId),
  }
}
