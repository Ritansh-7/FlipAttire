"use client"

import { useEffect, useState } from "react"
import HmHeader from "@modules/hm-storefront/hm-header"
import ProductImg from "@modules/hm-storefront/product-img"
import { useBag } from "@modules/hm-storefront/bag"
import { API, money, priceINR, type Item } from "@modules/hm-storefront/photos"
import { DEFAULT_CUSTOMER, getCustomerId, getLoginId, logoutCustomer, setCustomerId, setLoginId } from "@modules/hm-storefront/session"

type Preview = {
  customer_id: string
  variant: string
  experiment_id: string
  model_version: string
  top_departments: Record<string, number>
  past_purchases: number
  recommendations: { article_id: string; position: number; score: number; source: string; article?: Item }[]
}

type HistEvent = { event_type: string; article_id?: string; event_time: string; surface?: string }

export default function ProfilePage() {
  const [customer, setCustomer] = useState(DEFAULT_CUSTOMER)
  const [loginName, setLoginName] = useState("")
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [authError, setAuthError] = useState("")
  const [preview, setPreview] = useState<Preview | null>(null)
  const [orders, setOrders] = useState<HistEvent[]>([])
  const [orderItems, setOrderItems] = useState<Record<string, Item>>({})
  const [status, setStatus] = useState("")
  const { bag } = useBag()

  async function refresh(id: string) {
    setStatus("Loading your profile…")
    try {
      const [p, h] = await Promise.all([
        fetch(`${API}/v1/customers/${encodeURIComponent(id)}/preview?limit=8`).then((r) => r.json()),
        fetch(`${API}/v1/customers/${encodeURIComponent(id)}/events?limit=100`).then((r) => r.json()),
      ])
      setPreview(p)
      const buys = (h as HistEvent[]).filter((e) => e.event_type === "purchase" && e.article_id)
      setOrders(buys)
      setStatus("")
      if (buys.length) {
        const ids = [...new Set(buys.map((e) => e.article_id!))]
        const cat: Item[] = await fetch(
          `${API}/v1/catalog?${ids.map((a) => `ids=${encodeURIComponent(a)}`).join("&")}`
        ).then((r) => r.json()).catch(() => [])
        const map: Record<string, Item> = {}
        for (const it of cat) map[it.article_id] = it
        setOrderItems(map)
      } else {
        setOrderItems({})
      }
    } catch {
      setStatus("Profile service is starting — refresh in a moment.")
    }
  }

  useEffect(() => {
    const id = getCustomerId()
    setCustomer(id)
    setLoginName(getLoginId())
    void refresh(id)
  }, [])

  async function auth(mode: "login" | "register") {
    setAuthError("")
    if (!username.trim() || password.length < 4) {
      setAuthError("Please enter both a login ID and a password (min 4 characters).")
      return
    }
    try {
      const res = await fetch(`${API}/v1/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ login_id: username.trim(), password }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Login failed" }))
        setAuthError(mode === "login" ? "Incorrect ID or password." : (err.detail || "Could not create account."))
        return
      }
      const data = await res.json()
      setLoginId(data.login_id)
      setLoginName(data.login_id)
      setCustomerId(data.customer_id)
      setCustomer(data.customer_id)
      setPassword("")
      void refresh(data.customer_id)
    } catch {
      setAuthError("Could not reach the login service — please try again.")
    }
  }

  function logout() {
    logoutCustomer()
    setLoginName("")
    setUsername("")
    setPassword("")
    setCustomer(DEFAULT_CUSTOMER)
    void refresh(DEFAULT_CUSTOMER)
  }

  return (
    <div className="hm-page">
      <div className="hm-announcement">Your style profile · Recommendations follow your buys</div>
      <HmHeader bagCount={bag.length} customerShort={loginName || "Login"} onBag={() => { window.location.href = "/in" }} />
      <main>
        <section className="hm-edit">
          <div className="hm-heading">
            <div><p className="hm-kicker">Account</p><h2>Hello, shopper</h2></div>
          </div>

          <div className="hm-modal" style={{ position: "static", transform: "none", margin: "0 0 24px", maxWidth: 980 }}>
            <div>
              <p className="hm-kicker">Login — your ID, your recommendations</p>
              {loginName ? (
                <>
                  <p>Welcome back, <b>{loginName}</b>! 👋</p>
                  <p style={{ wordBreak: "break-all" }}>Your style ID: <b>{customer}</b></p>
                  <div style={{ display: "flex", gap: 8, marginTop: 8, flexWrap: "wrap" }}>
                    <button onClick={logout}>Logout</button>
                  </div>
                </>
              ) : (
                <>
                  <p>Sign in and get your own <b>personal style ID</b> — every purchase shapes recommendations made just for you.</p>
                  <label>Login ID<input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="e.g. priya123" style={{ width: "100%" }} /></label>
                  <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="min 4 chars" style={{ width: "100%" }} /></label>
                  {authError && <p style={{ color: "#b3261e" }}>{authError}</p>}
                  <div style={{ display: "flex", gap: 8, marginTop: 8, flexWrap: "wrap" }}>
                    <button className="hm-primary" onClick={() => void auth("login")}>Login</button>
                    <button onClick={() => void auth("register")}>Create account</button>
                  </div>
                </>
              )}
              <small>One shopper, one style ID — your taste follows you on every device.</small>
            </div>
          </div>

          {status && <p>{status}</p>}
          {preview && preview.recommendations.length > 0 && (
            <div className="hm-heading">
              <div><p className="hm-kicker">Made for you</p><h2>Fresh picks, just for you</h2></div>
            </div>
          )}
          {preview && (
            <div className="hm-grid">
              {preview.recommendations.map((r) => r.article && (
                <article key={r.article_id} onClick={() => { window.location.href = `/in/product/${encodeURIComponent(r.article_id)}` }}>
                  <ProductImg item={r.article} alt={r.article.product_type} />
                  <div><h3>{r.article.name}</h3><p>{r.article.product_type} · {r.article.colour_group}</p>
                    <footer><b>{money(priceINR(r.article))}</b></footer>
                  </div>
                </article>
              ))}
            </div>
          )}

          <div className="hm-heading" style={{ marginTop: 24 }}>
            <div><p className="hm-kicker">My orders</p><h2>What you've shopped</h2></div>
          </div>
          {orders.length === 0 && !status && <p>No orders yet — fall in love with something, and it will show up here. 🛍️</p>}
          {orders.length > 0 && (
            <div>
              {orders.map((e, i) => {
                const item = (e.article_id && orderItems[e.article_id]) || undefined
                return (
                  <div className="hm-bag-item" key={`${e.article_id}-${i}`}>
                    {item && <div style={{ width: 72, flexShrink: 0 }}><ProductImg item={item} alt={item.product_type} height={88} /></div>}
                    <div>
                      <b>{item ? item.name : e.article_id}</b>
                      <p>{item ? `${item.product_type} · ${money(priceINR(item))} · ` : ""}{String(e.event_time).slice(0, 10)}</p>
                    </div>
                    <span style={{ fontSize: 12, color: "#2e7d32", fontWeight: 700 }}>✓ Delivered</span>
                  </div>
                )
              })}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
