"use client"

import { useEffect, useMemo, useState } from "react"
import HmHeader from "./hm-header"
import ProductCard from "./product-card"
import ProductModal from "./product-modal"
import WishlistDrawer from "./wishlist-drawer"
import ProductImg from "./product-img"
import { addToBagStored, loadBag, removeFromBagStored, useBag } from "./bag"
import { useWishlist } from "./wishlist"
import { API, categories, family, genderBucket, matchesCollection, money, pickPhoto, priceINR, sendEvent, type Item, type RecoResult } from "./photos"
import { DEFAULT_CUSTOMER, getCustomerId, getLoginId } from "./session"

// Quick Category Avatars with Myntra-style circular previews
const CATEGORY_AVATARS = [
  { name: "All", label: "All Items", icon: "✨" },
  { name: "T-shirts & tops", label: "Tops & Tees", icon: "👕" },
  { name: "Trousers & bottoms", label: "Jeans & Pants", icon: "👖" },
  { name: "Dresses", label: "Dresses", icon: "👗" },
  { name: "Jackets & layers", label: "Jackets", icon: "🧥" },
  { name: "Shoes", label: "Footwear", icon: "👟" },
  { name: "Accessories", label: "Accessories", icon: "👜" },
]

function catalogPageUrl(navTab: string, category: string, query: string, offset: number) {
  const params = new URLSearchParams({ limit: "100", offset: String(offset) })
  if (navTab !== "ALL") params.set("audience", navTab)
  if (category !== "All") params.set("category", category)
  if (query.trim()) params.set("query", query.trim())
  return `${API}/v1/products?${params.toString()}`
}

export default function HMStorefront() {
  const [items, setItems] = useState<Item[]>([])
  const [result, setResult] = useState<RecoResult | null>(null)
  const [customerId, setCustomerId] = useState(DEFAULT_CUSTOMER)
  const [category, setCategory] = useState("All")
  const [query, setQuery] = useState("")
  const [selected, setSelected] = useState<Item | null>(null)
  const [bagOpen, setBagOpen] = useState(false)
  const [wishlistOpen, setWishlistOpen] = useState(false)
  const [checkoutOpen, setCheckoutOpen] = useState(false)
  const [loginName, setLoginName] = useState("")
  const [status, setStatus] = useState("Curating your edit…")
  const [toastMsg, setToastMsg] = useState("")
  const [featured, setFeatured] = useState<Item[]>([])
  const [featuredAnchor, setFeaturedAnchor] = useState("")

  const { bag, setBag } = useBag()
  const { wishlist, toggleWishlist, isWishlisted } = useWishlist()

  function triggerToast(msg: string) {
    setToastMsg(msg)
    setTimeout(() => setToastMsg(""), 3000)
  }

  async function load(customer = customerId) {
    setStatus("Curating your personal recommendation edit…")
    try {
      const response = await fetch(
        `${API}/v1/recommendations?customer_id=${encodeURIComponent(customer)}&surface=homepage&limit=60`
      )
      if (!response.ok) throw new Error("API offline")
      const nextResult: RecoResult = await response.json()
      const ids = nextResult.recommendations.map((item) => `ids=${encodeURIComponent(item.article_id)}`).join("&")
      let nextItems: Item[] = []

      if (ids) {
        const catalog = await fetch(`${API}/v1/catalog?${ids}`)
        if (catalog.ok) {
          nextItems = await catalog.json()
        }
      }

      if (!nextItems.length) {
        const fallback = await fetch(`${API}/v1/products?limit=24&offset=0`)
        if (fallback.ok) {
          const fallbackData: { items?: Item[] } = await fallback.json()
          nextItems = fallbackData.items || []
        }
      }

      setResult(nextResult)
      setItems(nextItems)
      setStatus(
        nextItems.length
          ? `${nextItems.length} curated pieces selected for your taste profile`
          : "Showing a broad product edit while the recommendation service rehydrates."
      )
      
    } catch {
      try {
        const fallback = await fetch(`${API}/v1/products?limit=24&offset=0`)
        if (fallback.ok) {
          const fallbackData: { items?: Item[] } = await fallback.json()
          setItems(fallbackData.items || [])
          setStatus("Recommendation service is reconnecting; showing catalog fallback.")
          return
        }
      } catch {
        // fall through to the offline message below
      }
      setStatus("Recommendation service connecting — click Refresh Edit to load live recommendations.")
    }
  }

  useEffect(() => {
    const currentCust = getCustomerId()
    setCustomerId(currentCust)
    setLoginName(getLoginId())
    setBag(loadBag())
    void load(currentCust)
    void loadFeatured(currentCust)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Gender tabs use the catalog's own labels (index_group/section) — no guessing.
  // MEN = Menswear only · WOMEN = Ladieswear + Divided · KIDS = Baby/Children.
  // Sport/H&M+ split by section. Nothing leaks across tabs.
  // Verified: W39.7k+D15.1k / M12.5k / K34.7k.
  const [navTab, setNavTab] = useState("ALL")
  const [extraItems, setExtraItems] = useState<Item[]>([])
  const [catalogOffset, setCatalogOffset] = useState(0)
  const [catalogHasMore, setCatalogHasMore] = useState(false)
  const [catalogLoading, setCatalogLoading] = useState(false)
  const [catalogError, setCatalogError] = useState("")

  const allItems = useMemo(() => {
    const seen = new Set<string>()
    return items.concat(extraItems).filter((i) => (seen.has(i.article_id) ? false : (seen.add(i.article_id), true)))
  }, [items, extraItems])

  function matchNav(item: Item) {
    switch (navTab) {
      case "KIDS": return genderBucket(item) === "KIDS"
      case "MEN": return genderBucket(item) === "MEN"
      case "BEAUTY":
      case "STUDIO":
      case "SALE": return matchesCollection(item, navTab)
      case "WOMEN": return genderBucket(item) === "WOMEN"
      default: return true
    }
  }

  const TAB_HEADINGS: Record<string, { kicker: string; title: string }> = {
    ALL: { kicker: "Selected for your taste profile", title: "Your Next Favourites" },
    WOMEN: { kicker: "Women's edit", title: "Picked for her" },
    MEN: { kicker: "Men's edit", title: "Picked for him" },
    KIDS: { kicker: "Kids' edit", title: "Little trendsetters" },
    BEAUTY: { kicker: "Beauty & glam", title: "Finishing touches" },
    STUDIO: { kicker: "Studio 2026", title: "The statement edit" },
    SALE: { kicker: "Promotional catalogue edit", title: "Offer selection" },
  }

  // Shop-style search: matches name, type, family, colour — singular/plural aware.
  // No match stays empty (with a hint) instead of silently showing everything.
  const visible = useMemo(() => {
    if (!allItems.length) return []
    const singular = (t: string) => {
      if (/ies$/.test(t) && t.length > 4) return t.slice(0, -3) + "y"
      if (/(ss|us|is)$/.test(t)) return t
      if (/(ses|xes|zes|ches|shes)$/.test(t)) return t.slice(0, -2)
      if (/s$/.test(t) && t.length > 3) return t.slice(0, -1)
      return t
    }
    const tokens = query.toLowerCase().trim().split(/\s+/).filter(Boolean)
    const filtered = allItems.filter((item) => {
      const matchCat =
        category === "All" ||
        family(item.product_type) === category

      const hay = `${item.name} ${item.product_type} ${item.department} ${item.colour_group} ${family(item.product_type)}`.toLowerCase()
      const matchQuery =
        !tokens.length ||
        tokens.every((tok) => {
          const forms = [tok, singular(tok)].filter((v, i, a) => v && a.indexOf(v) === i)
          return forms.some((form) => hay.includes(form))
        })

      return matchCat && matchQuery && matchNav(item)
    })
    return filtered
  }, [allItems, category, query, navTab])

  // Department/category browsing uses server-side catalog filters, not a
  // narrow slice of recommendations, so the selected edit stays in scope.
  useEffect(() => {
    const controller = new AbortController()
    setExtraItems([])
    setCatalogOffset(0)
    setCatalogHasMore(false)
    setCatalogError("")

    const timer = window.setTimeout(async () => {
      setCatalogLoading(true)
      try {
        const response = await fetch(catalogPageUrl(navTab, category, query, 0), { signal: controller.signal })
        if (!response.ok) throw new Error(`Catalog request failed (${response.status})`)
        const data: { items?: Item[] } = await response.json()
        const batch = data.items || []
        const recommendationIds = new Set(items.map((item) => item.article_id))
        const browseItems = batch.filter((item) => !recommendationIds.has(item.article_id))
        setExtraItems(browseItems)
        setCatalogOffset(batch.length)
        setCatalogHasMore(batch.length === 100)
      } catch (error) {
        if (!controller.signal.aborted) {
          setCatalogError(error instanceof Error ? error.message : "Catalog could not be loaded.")
        }
      } finally {
        if (!controller.signal.aborted) setCatalogLoading(false)
      }
    }, query.trim() ? 250 : 0)

    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [navTab, category, query, items.length])

  async function loadMoreCatalog() {
    if (catalogLoading || !catalogHasMore) return
    setCatalogLoading(true)
    setCatalogError("")
    try {
      const response = await fetch(catalogPageUrl(navTab, category, query, catalogOffset))
      if (!response.ok) throw new Error(`Catalog request failed (${response.status})`)
      const data: { items?: Item[] } = await response.json()
      const batch = data.items || []
      setExtraItems((current) => {
        const ids = new Set([...items, ...current].map((item) => item.article_id))
        return current.concat(batch.filter((item) => !ids.has(item.article_id)))
      })
      setCatalogOffset((offset) => offset + batch.length)
      setCatalogHasMore(batch.length === 100)
    } catch (error) {
      setCatalogError(error instanceof Error ? error.message : "More products could not be loaded.")
    } finally {
      setCatalogLoading(false)
    }
  }

  // Deduped photo per grid: walk each card's candidates skipping URLs already
  // shown above it — zero repeats on the page, stable for a given lineup.
  const photoMap = useMemo(() => {
    const used = new Set<string>()
    const map = new Map<string, string>()
    for (const item of visible) map.set(item.article_id, pickPhoto(item, used))
    return map
  }, [visible])

  const featuredPhotoMap = useMemo(() => {
    const used = new Set<string>()
    const map = new Map<string, string>()
    for (const item of featured) map.set(item.article_id, pickPhoto(item, used))
    return map
  }, [featured])

  const subtotal = bag.reduce((sum, item) => sum + priceINR(item), 0)

  function handleAddToBag(item: Item, size = "M") {
    addToBagStored(item)
    void sendEvent("add_to_cart", item, result)
    setSelected(null)
    triggerToast(`Added ${item.name} (${size}) to Bag! 🛍️`)
  }

  function handleToggleWishlist(item: Item, e?: React.MouseEvent) {
    if (e) e.stopPropagation()
    const added = toggleWishlist(item)
    triggerToast(added ? `Saved ${item.name} to Wishlist! ♥` : `Removed from Wishlist.`)
  }

  // "Your featured picks" — recommendations grown from THIS customer's purchases.
  async function loadFeatured(customer: string) {
    try {
      const ev = await fetch(`${API}/v1/customers/${encodeURIComponent(customer)}/events?limit=100`)
      const events: { event_type: string; article_id?: string }[] = await ev.json()
      const bought: string[] = []
      for (const e of events) {
        if (e.event_type === "purchase" && e.article_id && !bought.includes(e.article_id)) bought.push(e.article_id)
        if (bought.length >= 3) break
      }
      if (!bought.length) { setFeatured([]); setFeaturedAnchor(""); return }
      const seen = new Set(bought)
      const recIds: string[] = []
      for (const aid of bought) {
        const sim = await fetch(`${API}/v1/catalog/${encodeURIComponent(aid)}/similar?limit=6`)
        const arr: { article_id: string }[] = sim.ok ? await sim.json() : []
        for (const s of arr) {
          if (!seen.has(s.article_id)) { seen.add(s.article_id); recIds.push(s.article_id) }
        }
        if (recIds.length >= 12) break
      }

      // The item-similarity artifact is intentionally sparse: a purchased
      // article can have only one or zero neighbours.  Do not let that make
      // the featured section collapse to a single card.  Backfill from the
      // same ranked recommendation feed used by the main edit, preserving
      // the customer's experiment assignment and recommendation ordering.
      if (recIds.length < 12) {
        const fallback = await fetch(
          `${API}/v1/recommendations?customer_id=${encodeURIComponent(customer)}&surface=homepage&limit=12`
        )
        if (fallback.ok) {
          const ranked: { article_id: string }[] = (await fallback.json()).recommendations || []
          for (const recommendation of ranked) {
            if (!seen.has(recommendation.article_id)) {
              seen.add(recommendation.article_id)
              recIds.push(recommendation.article_id)
            }
            if (recIds.length >= 12) break
          }
        }
      }
      if (!recIds.length) { setFeatured([]); return }
      const cat = await fetch(`${API}/v1/catalog?${recIds.slice(0, 12).map((a) => `ids=${encodeURIComponent(a)}`).join("&")}`)
      const candidates: Item[] = await cat.json()
      const anchor = await fetch(`${API}/v1/catalog?ids=${encodeURIComponent(bought[0])}`)
      const anchorItems: Item[] = await anchor.json()
      const anchorBucket = anchorItems.length ? genderBucket(anchorItems[0]) : ""
      // Gender-aware: keep same-audience (+ unisex "") companions so a MEN
      // buy never shows WOMEN picks. Backfill if the filter empties the row.
      const matching = anchorBucket && ["MEN", "WOMEN", "KIDS"].includes(anchorBucket)
        ? candidates.filter((c) => ["", anchorBucket].includes(genderBucket(c)))
        : candidates
      setFeatured(matching.length ? matching : candidates)
      setFeaturedAnchor(anchorItems.length ? anchorItems[0].name : "")
    } catch {
      setFeatured([])
    }
  }

  function handleNavCategory(navCat: string) {
    const key = navCat === "STUDIO 2026" ? "STUDIO" : navCat
    if (["ALL", "WOMEN", "MEN", "KIDS", "BEAUTY", "STUDIO", "SALE"].includes(key)) {
      setNavTab(key)
      setCategory("All")
      setQuery("")
      document.getElementById("edit")?.scrollIntoView({ behavior: "smooth" })
    } else {
      setQuery(navCat)
    }
  }

  return (
    <div className="hm-page myntra-theme">
      {/* Toast Popup Notification */}
      {toastMsg && <div className="hm-toast-popup">{toastMsg}</div>}

      {/* Top Announcement Bar */}
      <div className="hm-announcement">
        FLIPATTIRE CATALOGUE · PERSONALIZED EDITS · FILTERED BY DEPARTMENT AND PRODUCT TYPE
      </div>

      {/* Main Header Component */}
      <HmHeader
        activeCategory={navTab === "STUDIO" ? "STUDIO 2026" : navTab}
        bagCount={bag.length}
        wishlistCount={wishlist.length}
        customerShort={loginName || "Login"}
        onBag={() => setBagOpen(true)}
        onWishlist={() => setWishlistOpen(true)}
        onSelectNavCategory={handleNavCategory}
        query={query}
        setQuery={setQuery}
        showSearch
      />

      <main id="top">
        {/* Editorial introduction */}
        <section className="hm-hero myntra-hero-slider">
          <div className="hero-copy-box">
            <span className="hm-kicker">CURATED PERSONAL EDIT · 2026</span>
            <h1>
              Wear what<br />
              <em>feels like you.</em>
            </h1>
            <p className="hero-desc">
              A calm, high-fashion edit built around your taste profile and live recommendation algorithm.
            </p>
            <div className="hero-cta-group">
              <a href="#edit" className="primary-hero-btn">
                Shop The Edit <span>→</span>
              </a>
              <span className="hero-offer-tag">A more considered way to discover</span>
            </div>
          </div>
          <div className="hm-hero-art">
            <div className="hero-badge-pill">THE STYLE EDIT</div>
            <div className="hero-discount-circle">CURATED FOR YOU</div>
          </div>
        </section>

        {/* Circular Category Avatars (Myntra Circle Bar) */}
        <section className="myntra-category-circles">
          <h3 className="section-subheading">EXPLORE CATEGORIES</h3>
          <div className="circle-avatars-row">
            {CATEGORY_AVATARS.map((cat) => (
              <button
                key={cat.name}
                className={`category-circle-item ${category === cat.name ? "active" : ""}`}
                onClick={() => {
                  setCategory(cat.name)
                  setQuery("")
                }}
              >
                <div className="circle-avatar-box">
                  <span className="avatar-icon">{cat.icon}</span>
                </div>
                <span className="circle-label">{cat.label}</span>
              </button>
            ))}
          </div>
        </section>

        {/* Recommendation Trust & Experiment Banner */}
        <section className="hm-trust">
          <div><b>PERSONALISED</b><span>Recommendations shaped by your activity</span></div>
          <div><b>CURATED CATALOGUE</b><span>Browse by audience and product type</span></div>
          <div><b>DEMO CHECKOUT</b><span>Explore the shopping flow without a real charge</span></div>
        </section>

        {/* Main Product Catalog & Edit Grid */}
        <section className="hm-edit" id="edit">
          <div className="hm-heading">
            <div>
              <p className="hm-kicker">{(TAB_HEADINGS[navTab] || TAB_HEADINGS.ALL).kicker}</p>
              <h2>{(TAB_HEADINGS[navTab] || TAB_HEADINGS.ALL).title} · {visible.length} styles</h2>
            </div>
            <div className="hm-customer">
              <div className="customer-info-pill" onClick={() => { window.location.href = "/in/profile" }}>
                <span>{loginName ? `Profile: ${loginName}` : "Login:"}</span> <b>{loginName || customerId.slice(0, 10) + "..."}</b>
              </div>
              <button onClick={() => { window.location.href = "/in/profile" }} className="switch-user-btn">
                {loginName ? "My Account" : "Login"}
              </button>
              <button onClick={() => void load()} className="refresh-edit-btn">
                Refresh Edit 🔄
              </button>
            </div>
          </div>

          <div className="hm-status">
            <span>{status}</span>
            <span>Variant: {result?.variant || "hybrid_v2"} · Engine: {result?.model_version || "hybrid_v2"}</span>
          </div>
          {navTab === "SALE" && (
            <p className="hm-catalog-note">
              This demo catalog has promotional product labels, but no verified sale prices or discount data.
            </p>
          )}

          {/* Product Cards Grid */}
          <div className="hm-grid myntra-product-grid">
            {visible.map((item) => (
              <ProductCard
                key={item.article_id}
                item={item}
                result={result}
                photoSrc={photoMap.get(item.article_id)}
                isWishlisted={isWishlisted(item.article_id)}
                onSelect={() => {
                  setSelected(item)
                  void sendEvent("view", item, result)
                }}
                onToggleWishlist={(e) => handleToggleWishlist(item, e)}
                onQuickAdd={(e) => {
                  e.stopPropagation()
                  void sendEvent("click", item, result)
                  handleAddToBag(item)
                }}
              />
            ))}
          </div>
          {catalogError && <p className="hm-catalog-error" role="alert">{catalogError}</p>}
          {catalogHasMore && (
            <button className="hm-load-more" onClick={() => void loadMoreCatalog()} disabled={catalogLoading}>
              {catalogLoading ? "Loading products…" : "Load more"}
            </button>
          )}
          {catalogLoading && !visible.length && <p className="hm-status">Loading matching products…</p>}
          {visible.length === 0 && allItems.length > 0 && (
            <p className="hm-status" style={{ marginTop: 16 }}>
              No matches for “{query}” in this edit — try “jeans”, “dress”, “sneakers” or clear the search.
            </p>
          )}
        </section>

        {/* Your Featured Picks — grown from this customer's purchases */}
        {navTab === "ALL" && category === "All" && !query && featured.length > 0 && (
          <section className="hm-edit" id="featured">
            <div className="hm-heading">
              <div>
                <p className="hm-kicker">Your featured picks</p>
                <h2>Because you shopped with us</h2>
              </div>
            </div>
            {featuredAnchor && (
              <p style={{ margin: "0 0 16px", fontSize: 14 }}>
                Inspired by your buy: <b>{featuredAnchor}</b> — companions picked for that taste.
              </p>
            )}
            <div className="hm-grid myntra-product-grid">
              {featured.map((item) => (
                <ProductCard
                  key={`featured-${item.article_id}`}
                  item={item}
                result={result}
                  photoSrc={featuredPhotoMap.get(item.article_id)}
                  isWishlisted={isWishlisted(item.article_id)}
                  onSelect={() => {
                    setSelected(item)
                    void sendEvent("view", item, result)
                  }}
                  onToggleWishlist={(e) => handleToggleWishlist(item, e)}
                  onQuickAdd={(e) => {
                    e.stopPropagation()
                    void sendEvent("click", item, result)
                    handleAddToBag(item)
                  }}
                />
              ))}
            </div>
          </section>
        )}

        {/* Story & Transparency Band */}
        <section className="hm-story">
          <div>
            <p className="hm-kicker">MADE FOR YOU</p>
            <h2>New favourites, every single week.</h2>
          </div>
          <p>
            Fresh drops, seasonal must-haves and timeless staples — handpicked around what you love,
            so your wardrobe never goes out of style.
          </p>
          <p style={{ fontSize: 11, opacity: 0.7 }}>Fashion photos via <a href="https://www.pexels.com" target="_blank" rel="noreferrer">Pexels</a> & <a href="https://pixabay.com" target="_blank" rel="noreferrer">Pixabay</a> · Garment archive via Wikimedia Commons</p>
        </section>
      </main>

      {/* Product Quick View Modal */}
      {selected && (
        <ProductModal
          item={selected}
          isWishlisted={isWishlisted(selected.article_id)}
          onClose={() => setSelected(null)}
          onAddToBag={(item, size) => handleAddToBag(item, size)}
          onToggleWishlist={(item) => handleToggleWishlist(item)}
        />
      )}

      {/* Wishlist Drawer */}
      {wishlistOpen && (
        <WishlistDrawer
          wishlist={wishlist}
          onClose={() => setWishlistOpen(false)}
          onMoveToBag={(item) => {
            handleAddToBag(item)
            toggleWishlist(item)
          }}
          onRemove={(aid) => {
            const item = wishlist.find((x) => x.article_id === aid)
            if (item) toggleWishlist(item)
          }}
        />
      )}

      {/* Customer login lives on the profile page (/in/profile) */}

      {/* Shopping Bag Drawer */}
      {bagOpen && (
        <div className="hm-overlay" onClick={() => setBagOpen(false)}>
          <aside className="hm-bag" onClick={(event) => event.stopPropagation()}>
            <button onClick={() => setBagOpen(false)} className="hm-close">
              ×
            </button>
            <h2>Your Shopping Bag ({bag.length})</h2>
            {bag.length ? (
              bag.map((item) => (
                <div className="hm-bag-item" key={item.article_id}>
                  <div style={{ width: 72, flexShrink: 0 }}>
                    <ProductImg item={item} alt={item.product_type} height={88} />
                  </div>
                  <div>
                    <b>{item.name}</b>
                    <p>
                      {item.product_type} · {money(priceINR(item))}
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      removeFromBagStored(item.article_id)
                      setBag(loadBag())
                    }}
                  >
                    ×
                  </button>
                </div>
              ))
            ) : (
              <p>Your bag is waiting for something special.</p>
            )}
            <div className="hm-bag-total">
              <span>Subtotal</span>
              <b>₹{Math.round(subtotal).toLocaleString("en-IN")}</b>
            </div>
            <button
              className="hm-primary"
              disabled={!bag.length}
              onClick={() => {
                setBagOpen(false)
                setCheckoutOpen(true)
              }}
            >
              Continue to Checkout →
            </button>
          </aside>
        </div>
      )}

      {/* Demo Checkout Modal */}
      {checkoutOpen && (
        <div className="hm-overlay">
          <form
            className="hm-checkout"
            onSubmit={(event) => {
              event.preventDefault()
              bag.forEach((item) => void sendEvent("purchase", item, result))
              setBag([])
              setCheckoutOpen(false)
              triggerToast("Order placed successfully! 🎉 Demo payment approved.")
              void loadFeatured(customerId)
            }}
          >
            <button type="button" onClick={() => setCheckoutOpen(false)} className="hm-close">
              ×
            </button>
            <p className="hm-kicker">SECURE CHECKOUT</p>
            <h2>Complete Your Order</h2>
            <input required placeholder="Full Name" />
            <textarea required placeholder="Delivery Address" />
            <select defaultValue="UPI">
              <option>UPI (Google Pay / PhonePe / Paytm)</option>
              <option>Credit / Debit Card</option>
              <option>Cash on Delivery</option>
            </select>
            <button className="hm-primary">Pay &amp; Place Order</button>
            <small>Demo checkout flow · No actual card charge is made.</small>
          </form>
        </div>
      )}
    </div>
  )
}

