"use client"

import { useEffect, useMemo, useState } from "react"
import HmHeader from "@modules/hm-storefront/hm-header"
import ProductImg from "@modules/hm-storefront/product-img"
import { addToBagStored, useBag } from "@modules/hm-storefront/bag"
import { API, categories, family, money, pickPhoto, priceINR, sendRawEvent, type Item } from "@modules/hm-storefront/photos"
import { DEFAULT_CUSTOMER, getCustomerId, getLoginId } from "@modules/hm-storefront/session"

const DEPARTMENTS = ["All departments", "Ladies", "Menswear", "Divided", "Kids", "Baby", "Sport"]

export default function ShopPage() {
  const [customer, setCustomer] = useState(DEFAULT_CUSTOMER)
  const [loginName, setLoginName] = useState("")
  const [items, setItems] = useState<Item[]>([])
  const [query, setQuery] = useState("")
  const [category, setCategory] = useState("All")
  const [department, setDepartment] = useState("All departments")
  const [offset, setOffset] = useState(0)
  const [status, setStatus] = useState("Loading products…")
  const { bag, setBag } = useBag()
  const [bagOpen, setBagOpen] = useState(false)
  const LIMIT = 48

  async function load(reset = true) {
    const off = reset ? 0 : offset
    setStatus("Loading products…")
    try {
      const params = new URLSearchParams({ limit: String(LIMIT), offset: String(off) })
      if (query.trim()) params.set("query", query.trim())
      if (department !== "All departments") params.set("department", department)
      const res = await fetch(`${API}/v1/products?${params}`)
      const data = await res.json()
      const next: Item[] = data.items || []
      setItems(reset ? next : [...items, ...next])
      setOffset(off + next.length)
      setStatus(next.length < LIMIT ? `${(reset ? next.length : items.length + next.length)} products` : "Keep scrolling for more")
    } catch {
      setStatus("Product service is starting — refresh in a moment.")
    }
  }

  useEffect(() => { setCustomer(getCustomerId()); setLoginName(getLoginId()); void load(true) }, [])

  const visible = items.filter((item) => category === "All" || family(item.product_type) === category)

  const shopPhotos = useMemo(() => {
    const used = new Set<string>()
    const map = new Map<string, string>()
    for (const item of visible) map.set(item.article_id, pickPhoto(item, used))
    return map
  }, [visible])

  return (
    <div className="hm-page">
      <div className="hm-announcement">1,00,000+ products · Personalised for your style</div>
      <HmHeader bagCount={bag.length} customerShort={loginName || "Login"} onBag={() => setBagOpen(true)} />
      <main>
        <section className="hm-edit" id="edit">
          <div className="hm-heading">
            <div><p className="hm-kicker">Full catalogue</p><h2>Shop all</h2></div>
            <div className="hm-customer">
              <label>Search<input value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") void load(true) }} placeholder="jeans, dress, jacket…" /></label>
              <button onClick={() => void load(true)}>Search</button>
            </div>
          </div>
          <div className="hm-categories">
            {DEPARTMENTS.map((d) => <button className={department === d ? "active" : ""} key={d} onClick={() => { setDepartment(d); }} onDoubleClick={() => void load(true)}>{d}</button>)}
          </div>
          <div className="hm-categories">
            {categories.map((c) => <button className={category === c ? "active" : ""} key={c} onClick={() => setCategory(c)}>{c}</button>)}
          </div>
          <div className="hm-status"><span>{status}</span><span><button onClick={() => void load(true)}>Apply filters</button></span></div>
          <div className="hm-grid">
            {visible.map((item) => (
              <article key={item.article_id} onClick={() => { window.location.href = `/in/product/${encodeURIComponent(item.article_id)}` }}>
                <ProductImg item={item} alt={`${item.product_type} in ${item.colour_group}`} src={shopPhotos.get(item.article_id)} />
                <div><h3>{item.name}</h3><p>{item.product_type} · {item.colour_group}</p>
                  <footer><b>{money(priceINR(item))}</b>
                    <button onClick={(e) => { e.stopPropagation(); void sendRawEvent("click", customer, item, "shop"); void sendRawEvent("add_to_cart", customer, item, "shop"); addToBagStored(item); setBag([...bag, item].filter((x, i, a) => a.findIndex((y) => y.article_id === x.article_id) === i)) }} aria-label="Add to bag">♡</button>
                  </footer>
                </div>
              </article>
            ))}
          </div>
          <div style={{ textAlign: "center", margin: "24px 0" }}><button className="hm-primary" onClick={() => void load(false)}>Load more</button></div>
        </section>
      </main>
      {bagOpen && <div className="hm-overlay" onClick={() => setBagOpen(false)}><aside className="hm-bag" onClick={(e) => e.stopPropagation()}><button onClick={() => setBagOpen(false)} className="hm-close">×</button><h2>Your bag</h2><p>{bag.length} item(s). Checkout lives on the <a href="/in">homepage</a>.</p><a href="/in"><button className="hm-primary">Go to checkout</button></a></aside></div>}
    </div>
  )
}
