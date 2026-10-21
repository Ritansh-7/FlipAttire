"use client"

import { useEffect, useState } from "react"
import type { Item } from "./photos"
import { BAG_KEY } from "./session"

export function loadBag(): Item[] {
  if (typeof window === "undefined") return []
  try {
    const raw = localStorage.getItem(BAG_KEY)
    return raw ? (JSON.parse(raw) as Item[]) : []
  } catch {
    return []
  }
}

export function saveBag(bag: Item[]) {
  try {
    localStorage.setItem(BAG_KEY, JSON.stringify(bag))
  } catch {
    /* storage full or blocked — bag just won't persist */
  }
  window.dispatchEvent(new Event("hm:bag"))
}

export function addToBagStored(item: Item) {
  const bag = loadBag()
  if (!bag.some((entry) => entry.article_id === item.article_id)) {
    bag.push(item)
    saveBag(bag)
  }
}

export function removeFromBagStored(articleId: string) {
  saveBag(loadBag().filter((entry) => entry.article_id !== articleId))
}

/** Shared bag state synced across pages via localStorage + window events. */
export function useBag() {
  const [bag, setBag] = useState<Item[]>([])
  useEffect(() => {
    setBag(loadBag())
    const sync = () => setBag(loadBag())
    window.addEventListener("hm:bag", sync)
    window.addEventListener("storage", sync)
    return () => {
      window.removeEventListener("hm:bag", sync)
      window.removeEventListener("storage", sync)
    }
  }, [])
  return { bag, setBag: (next: Item[]) => { setBag(next); saveBag(next) } }
}
