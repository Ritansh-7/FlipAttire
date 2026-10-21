export type Item = {
  article_id: string
  name: string
  description?: string
  product_type: string
  department: string
  colour_group: string
  price: number
  image_data?: string
  index_group?: string
  section?: string
}

export type Reco = { article_id: string; position: number; score: number; source: string }

export type RecoResult = {
  request_id: string
  customer_id: string
  experiment_id: string
  variant: string
  model_version: string
  recommendations: Reco[]
}

export const API = process.env.NEXT_PUBLIC_RECOMMENDER_URL || "http://127.0.0.1:8000"

export const categories = ["All", "T-shirts & tops", "Trousers & bottoms", "Dresses", "Jackets & layers", "Shoes", "Accessories"]

export function family(value: string) {
  // Order matters: bottoms/dresses first so "underwear tights" lands in
  // bottoms, not tops. Covers 99.5%+ of the 131 catalog product types.
  const text = (value || "").toLowerCase()
  if (/trouser|pants|jeans|shorts|skirt|legging|\btights\b|jogger|dungaree|sarong|overall|underwear bottom|underwear tights|swimwear bottom|pyjama bottom|long john/.test(text)) return "Trousers & bottoms"
  if (/dress|jumpsuit|playsuit|\bgown\b|frock|underdress/.test(text)) return "Dresses"
  if (/t-shirt|\btee\b|blouse|polo|\bshirt\b|\btop\b|vest|sweater|knit|sweatshirt|bodysuit|\bbra\b|lingerie|pyjama|nightwear|bikini|camisole|swimwear|swimsuit|underwear|corset|garment set/.test(text)) return "T-shirts & tops"
  if (/jacket|coat|blazer|cardigan|hoodie|parka|waistcoat|robe|outerwear/.test(text)) return "Jackets & layers"
  if (/shoe|boot|sandal|sneaker|loafer|heel|slipper|ballerina|pump|wedge|moccasin|flip.flop|flat shoe|pre-walk|bootie/.test(text)) return "Shoes"
  if (/bag|backpack|bumbag|tote|wallet|belt|scarf|\bhat\b|beanie|\bcapp?\b|accessor|sock|leg warmer|earring|necklace|bracelet|jewel|ring|sunglass|watch|glove|suspender|brace|tie|hair|headband|alice|clip|keychain|umbrella|eyeglass/.test(text)) return "Accessories"
  return "All"
}

export function genderBucket(item: Item) {
  const g = (item.index_group || "").toLowerCase()
  const s = (item.section || "").toLowerCase()
  if (g === "baby/children" || /\b(baby|kids?|children|young boy|young girl)\b/.test(s)) return "KIDS"
  if (g === "menswear") return "MEN"
  if (g === "ladieswear" || g === "divided") return "WOMEN"
  if (/\bmen(?:s)?\b/.test(s) && !/\bwomen(?:s)?\b/.test(s)) return "MEN"
  if (/\b(ladies|women|mama|divided)\b/.test(s)) return "WOMEN"
  return ""
}

export function matchesCollection(item: Item, collection: string) {
  const department = (item.department || "").toLowerCase().trim()
  const section = (item.section || "").toLowerCase().trim()
  const productType = (item.product_type || "").toLowerCase().trim()

  if (collection === "BEAUTY") {
    if (genderBucket(item) === "KIDS") return false
    const nameAndDescription = `${item.name} ${item.description || ""}`.toLowerCase()
    if (/\bbags?\b|(?:cosmetic|make[- ]?up|lipstick)\s*bags?\b/.test(nameAndDescription)) return false
    if (/cosmetic|fragrance|perfume|make.?up|skin.?care|hair.?care|nail.?care|shampoo|conditioner|lip.?balm|lipstick|deodorant|bath.?bomb/.test(productType)) return true
    if (!["Accessories", "All"].includes(family(productType))) return false
    return /perfume|fragrance|eau de parfum|eau de toilette|shampoo|conditioner|skin.?care|hair.?care|nail polish|lip.?balm|lipstick|foundation|mascara|eyeliner|deodorant|lotion|bath.?bomb/.test(nameAndDescription)
  }
  if (collection === "STUDIO") {
    const studioLabels = new Set([
      "studio collection",
      "limited edition",
      "special collection",
      "special collections",
      "conscious exclusive",
      "collaborations",
    ])
    return studioLabels.has(department) || studioLabels.has(section)
  }
  if (collection === "SALE") {
    return /promotion\s*\/?\s*other\s*\/?\s*offer|price items/.test(department)
  }
  return false
}

/** Exact Pexels pool for this product: garment-specific first, then gender-aware. */
export function photoPoolKey(item: Item) {
  const t = (item.product_type || "").toLowerCase()
  if (/sock/.test(t)) return "socks"
  if (/swimwear|swimsuit|bikini/.test(t)) return "swimwear"
  if (/\bbelt\b/.test(t)) return "belts"
  const bucket = genderBucket(item)
  if (bucket === "KIDS") return "kids"
  const fam = family(item.product_type || "")
  if (fam === "T-shirts & tops") return bucket === "MEN" ? "tops_men" : bucket === "WOMEN" ? "tops_women" : "tops"
  if (fam === "Trousers & bottoms") return bucket === "MEN" ? "bottoms_men" : bucket === "WOMEN" ? "bottoms_women" : "bottoms"
  if (fam === "Jackets & layers") return bucket === "MEN" ? "jackets_men" : bucket === "WOMEN" ? "jackets_women" : "jackets"
  if (fam === "Dresses") return "dresses"
  if (fam === "Shoes") return "shoes"
  if (fam === "Accessories") return "accessories"
  return ""
}

export function hashId(id: string) {
  let h = 0
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0
  return h
}

/** Demo price: catalog parquet ships price 0, so derive a stable price per article. */
export function priceINR(item: Item) {
  const v = Number(item.price || 0)
  if (v > 0) return Math.round(v * 83)
  return 499 + (hashId(item.article_id) % 2000)
}

export function money(value: number, articleId?: string) {
  if (value > 0) return `₹${Math.round(value).toLocaleString("en-IN")}`
  const fake: Item = { article_id: articleId || "x", name: "", product_type: "", department: "", colour_group: "", price: 0 }
  return `₹${priceINR(fake).toLocaleString("en-IN")}`
}

const FASHION_PHOTOS: Record<string, string[]> = {
  "T-shirts & tops": [
    "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600&h=750&fit=crop&auto=format&q=80",
    "https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=600&h=750&fit=crop&auto=format&q=80",
    "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?w=600&h=750&fit=crop&auto=format&q=80",
    "https://images.unsplash.com/photo-1503341504253-dff4815485f1?w=600&h=750&fit=crop&auto=format&q=80",
  ],
  "Trousers & bottoms": [
    "https://images.unsplash.com/photo-1542272604-787c3835535d?w=600&h=750&fit=crop&auto=format&q=80",
    "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=600&h=750&fit=crop&auto=format&q=80",
    "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=600&h=750&fit=crop&auto=format&q=80",
  ],
  Dresses: [
    "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=600&h=750&fit=crop&auto=format&q=80",
    "https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?w=600&h=750&fit=crop&auto=format&q=80",
    "https://images.unsplash.com/photo-1496747611176-843222e1e57c?w=600&h=750&fit=crop&auto=format&q=80",
  ],
  "Jackets & layers": [
    "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=600&h=750&fit=crop&auto=format&q=80",
    "https://images.unsplash.com/photo-1544022613-e87ca75a784a?w=600&h=750&fit=crop&auto=format&q=80",
    "https://images.unsplash.com/photo-1434389677669-e08b4cac3105?w=600&h=750&fit=crop&auto=format&q=80",
  ],
  Shoes: [
    "https://images.unsplash.com/photo-1549298916-b41d501d3772?w=600&h=750&fit=crop&auto=format&q=80",
    "https://images.unsplash.com/photo-1560343090-f0409e92791a?w=600&h=750&fit=crop&auto=format&q=80",
    "https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?w=600&h=750&fit=crop&auto=format&q=80",
  ],
  Accessories: [
    "https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=600&h=750&fit=crop&auto=format&q=80",
    "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&h=750&fit=crop&auto=format&q=80",
    "https://images.unsplash.com/photo-1611652022419-a9419f74343d?w=600&h=750&fit=crop&auto=format&q=80",
  ],
  All: [
    "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=600&h=750&fit=crop&auto=format&q=80",
    "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=600&h=750&fit=crop&auto=format&q=80",
    "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=600&h=750&fit=crop&auto=format&q=80",
  ],
}

import { GARMENT_PHOTOS } from "./garment-photos"
import { PEXELS_PHOTOS } from "./pexels-photos"
import { PIXABAY_PHOTOS } from "./pixabay-photos"

const GARMENT_POOL: Record<string, string> = {
  "T-shirts & tops": "tops",
  "Trousers & bottoms": "bottoms",
  Dresses: "dresses",
  "Jackets & layers": "jackets",
  Shoes: "shoes",
  Accessories: "accessories",
}

function poolPick(pools: Record<string, string[]>, item: Item) {
  const key = GARMENT_POOL[family(item.product_type || "")]
  const names = key ? [key] : Object.keys(pools)
  const name = names[hashId(item.article_id) % names.length]
  const pool = pools[name] || []
  if (pool.length) return pool[hashId(item.article_id + name) % pool.length]
  return ""
}

function poolPickAll(pools: Record<string, string[]>, item: Item): string[] {
  const key = GARMENT_POOL[family(item.product_type || "")]
  if (key && pools[key]) return pools[key]
  const all: string[] = []
  for (const name of Object.keys(pools)) for (const u of pools[name]) if (!all.includes(u)) all.push(u)
  return all
}

/**
 * Pick a photo no other visible card is using.
 * Tier 0 = exact pool (right gender + right garment). Walk stays INSIDE it,
 * so a clash never leaks into another gender/garment — repeat of a correct
 * photo beats showing a wrong one. Only when the exact pool itself is empty
 * do we fall back to same-family generic pools, then anything.
 */
const GARMENT_EXACT = new Set(["socks", "swimwear", "belts", "kids"])

function walkUnused(arr: string[], startSeed: string, used?: Set<string>): string {
  if (!arr.length) return ""
  const start = hashId(startSeed) % arr.length
  if (used) {
    for (let n = 0; n < arr.length; n++) {
      const u = arr[(start + n) % arr.length]
      if (!used.has(u)) { used.add(u); return u }
    }
    return "" // pool exhausted — caller decides next tier
  }
  return arr[start]
}

export function pickPhoto(item: Item, used?: Set<string>): string {
  const key = photoPoolKey(item)
  const exact = (key && PEXELS_PHOTOS[key]) || []
  // Tier 0: exact pool.
  let u = walkUnused(exact, item.article_id, used)
  if (u) return u
  if (!used) return exact.length ? exact[hashId(item.article_id) % exact.length] : ""
  // Tier 1 (only when the exact pool is exhausted): same-garment generic
  // pools — but never for garment-specific pools (socks/swimwear/belts/kids),
  // where any generic photo would be the wrong garment.
  if (!GARMENT_EXACT.has(key)) {
    const fam: string[] = []
    const pushFam = (arr: string[] | undefined) => {
      for (const x of arr || []) if (x && !fam.includes(x)) fam.push(x)
    }
    pushFam(poolPickAll(PEXELS_PHOTOS, item))
    pushFam(poolPickAll(PIXABAY_PHOTOS, item))
    pushFam(poolPickAll(GARMENT_PHOTOS, item))
    u = walkUnused(fam, item.article_id, used)
    if (u) return u
  }
  // Tier 2: repeat a correct photo rather than show a wrong one.
  if (exact.length) {
    const r = exact[hashId(item.article_id) % exact.length]
    used.add(r)
    return r
  }
  return ""
}

export function photoUrl(item: Item) {
  // Exact pool first (gender + garment aware, stable per article), so a men's
  // tee shows a man and socks show socks. Falls back to the ~50/50 mix, then
  // Commons garment shots. Photo stays stable across reloads.
  const key = photoPoolKey(item)
  if (key) {
    const arr = PEXELS_PHOTOS[key] || []
    if (arr.length) return arr[hashId(item.article_id) % arr.length]
  }
  const primary = hashId("px:" + item.article_id) % 2 === 0 ? PEXELS_PHOTOS : PIXABAY_PHOTOS
  const secondary = primary === PEXELS_PHOTOS ? PIXABAY_PHOTOS : PEXELS_PHOTOS
  return poolPick(primary, item) || poolPick(secondary, item) || poolPick(GARMENT_PHOTOS, item)
}

export function pixabayPhotoUrl(item: Item) {
  // Second source: Pixabay fashion photo from the matching pool.
  return poolPick(PIXABAY_PHOTOS, item)
}

export function garmentPhotoUrl(item: Item) {
  // Backup: Commons garment photo from the matching pool.
  return poolPick(GARMENT_PHOTOS, item)
}

export function categoryPhotoUrl(item: Item) {
  // Fashion-category backup if the unique photo ever fails to load.
  const pool = FASHION_PHOTOS[family(item.product_type || "")] || FASHION_PHOTOS.All
  return pool[hashId(item.article_id) % pool.length]
}

export function fallbackUrl(item: Item) {
  return item.image_data || `${API}/v1/catalog/${encodeURIComponent(item.article_id)}/image`
}

export async function sendRawEvent(
  type: string,
  customerId: string,
  item: Item,
  surface = "shop"
) {
  await fetch(`${API}/v1/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      event_type: type,
      customer_id: customerId,
      article_id: item.article_id,
      surface,
    }),
  }).catch(() => undefined)
}

export async function sendEvent(
  type: string,
  item: Item,
  current: RecoResult | null,
  surface = "homepage"
) {
  if (!current) return
  await fetch(`${API}/v1/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      event_type: type,
      customer_id: current.customer_id,
      article_id: item.article_id,
      surface,
      request_id: current.request_id,
      experiment_id: current.experiment_id,
      variant: current.variant,
    }),
  }).catch(() => undefined)
}
