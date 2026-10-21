"use client"

import { use, useEffect, useState } from "react"
import HmHeader from "@modules/hm-storefront/hm-header"
import ProductImg from "@modules/hm-storefront/product-img"
import { addToBagStored, useBag } from "@modules/hm-storefront/bag"
import { API, money, priceINR, sendEvent, type Item, type RecoResult } from "@modules/hm-storefront/photos"
import { DEFAULT_CUSTOMER, getCustomerId, getLoginId } from "@modules/hm-storefront/session"

export default function ProductPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const [customer, setCustomer] = useState(DEFAULT_CUSTOMER)
  const [loginName, setLoginName] = useState("")
  const [item, setItem] = useState<Item | null>(null)
  const [similar, setSimilar] = useState<Item[]>([])
  const [result, setResult] = useState<RecoResult | null>(null)
  const [status, setStatus] = useState("Loading product…")
  const { bag } = useBag()
  const [added, setAdded] = useState(false)

  useEffect(() => {
    setCustomer(getCustomerId())
    setLoginName(getLoginId())
    async function run() {
      try {
        const reco = await fetch(`${API}/v1/recommendations?customer_id=${encodeURIComponent(getCustomerId())}&surface=product&limit=4`)
        const recoJson: RecoResult = await reco.json()
        setResult(recoJson)
        const cat = await fetch(`${API}/v1/catalog?ids=${encodeURIComponent(id)}`)
        const items: Item[] = await cat.json()
        if (items.length) {
          setItem(items[0])
          setStatus("")
          void sendEvent("view", items[0], recoJson, "product")
        } else setStatus("Product not found.")
        const sim = await fetch(`${API}/v1/catalog/${encodeURIComponent(id)}/similar?limit=8`)
        const simIds: Item[] = await sim.json()
        if (simIds.length) {
          const full = await fetch(`${API}/v1/catalog?${simIds.map((s) => `ids=${encodeURIComponent(s.article_id)}`).join("&")}`)
          setSimilar(await full.json())
        }
      } catch {
        setStatus("Product service is starting — refresh in a moment.")
      }
    }
    void run()
  }, [id])

  return (
    <div className="hm-page">
      <div className="hm-announcement">Free delivery over ₹1,999</div>
      <HmHeader bagCount={bag.length} customerShort={loginName || "Login"} onBag={() => { window.location.href = "/in" }} />
      <main>
        <section className="hm-edit">
          <p className="hm-kicker"><a href="/in">Home</a> / <a href="/in/shop">Shop all</a> / {id}</p>
          {status && <p>{status}</p>}
          {item && (
            <div className="hm-modal" style={{ position: "static", transform: "none", margin: "0 auto", maxWidth: 980 }}>
              <ProductImg item={item} alt={item.product_type} height={480} />
              <div>
                <p className="hm-kicker">{item.department}</p>
                <h2>{item.name}</h2>
                <p>{item.product_type} · {item.department} · {item.colour_group}</p>
                <b className="hm-price">{money(priceINR(item))}</b>
                <p>{item.description || "A considered piece selected for your personal edit."}</p>
                <button className="hm-primary" onClick={() => { addToBagStored(item); void sendEvent("add_to_cart", item, result, "product"); setAdded(true) }}>
                  {added ? "Added ✓ — checkout on homepage" : "Add to bag"}
                </button>
                {added && <p><a href="/in">Go to bag & checkout →</a></p>}
              </div>
            </div>
          )}
          {similar.length > 0 && (
            <>
              <div className="hm-heading"><div><p className="hm-kicker">Pairs well with</p><h2>You may also like</h2></div></div>
              <div className="hm-grid">
                {similar.map((s) => (
                  <article key={s.article_id} onClick={() => { window.location.href = `/in/product/${encodeURIComponent(s.article_id)}` }}>
                    <ProductImg item={s} alt={s.product_type} />
                    <div><h3>{s.name}</h3><p>{s.product_type} · {s.colour_group}</p>
                      <footer><b>{money(priceINR(s))}</b><button onClick={(e) => { e.stopPropagation(); addToBagStored(s) }} aria-label="Add to bag">♡</button></footer>
                    </div>
                  </article>
                ))}
              </div>
            </>
          )}
        </section>
      </main>
    </div>
  )
}
