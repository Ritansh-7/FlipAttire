"use client"

import { useEffect, useState } from "react"
import ProductImg from "./product-img"
import { API, money, priceINR, type Item } from "./photos"

export default function ProductModal({
  item,
  isWishlisted,
  onClose,
  onAddToBag,
  onToggleWishlist,
}: {
  item: Item
  isWishlisted: boolean
  onClose: () => void
  onAddToBag: (item: Item, size: string) => void
  onToggleWishlist: (item: Item) => void
}) {
  const [selectedSize, setSelectedSize] = useState("M")
  const [pincode, setPincode] = useState("")
  const [pincodeMsg, setPincodeMsg] = useState("")
  const [similarItems, setSimilarItems] = useState<Item[]>([])

  const currentPrice = priceINR(item)
  const originalPrice = Math.round(currentPrice * 1.6)
  const discountPct = 37

  useEffect(() => {
    // Fetch similar items from API endpoint
    async function loadSimilar() {
      try {
        const res = await fetch(`${API}/v1/catalog/${encodeURIComponent(item.article_id)}/similar?limit=6`)
        if (res.ok) {
          const data: Item[] = await res.json()
          setSimilarItems(data)
        }
      } catch {
        /* fallback empty */
      }
    }
    void loadSimilar()
  }, [item.article_id])

  const checkDelivery = () => {
    if (!pincode.trim() || pincode.trim().length < 6) {
      setPincodeMsg("Please enter a valid 6-digit Pincode.")
      return
    }
    setPincodeMsg(`Express delivery available to ${pincode} by tomorrow! 🚀`)
  }

  return (
    <div className="hm-overlay" onClick={onClose}>
      <div className="hm-modal product-detail-modal" onClick={(e) => e.stopPropagation()}>
        <button onClick={onClose} className="hm-close" aria-label="Close product view">
          ×
        </button>

        <div className="modal-left-art">
          <ProductImg item={item} alt={item.name} />
          <div className="modal-rating-tag">4.3 ★ | 1.8k Ratings</div>
        </div>

        <div className="modal-right-details">
          <p className="modal-kicker">H&amp;M EDITION · PERSONAL SELECTION</p>
          <h2 className="modal-title">{item.name}</h2>
          <p className="modal-meta">{item.product_type} · {item.department} · {item.colour_group}</p>

          <div className="modal-price-box">
            <span className="modal-current-price">{money(currentPrice)}</span>
            <span className="modal-original-price">{money(originalPrice)}</span>
            <span className="modal-discount-tag">({discountPct}% OFF)</span>
            <div className="tax-inclusive">Inclusive of all taxes</div>
          </div>

          <hr className="modal-divider" />

          {/* Size Selector */}
          <div className="size-selector-box">
            <div className="size-header">
              <span>SELECT SIZE</span>
              <span className="size-chart-link">SIZE CHART 📏</span>
            </div>
            <div className="size-pills">
              {["S", "M", "L", "XL", "XXL"].map((sz) => (
                <button
                  key={sz}
                  className={`size-btn ${selectedSize === sz ? "active" : ""}`}
                  onClick={() => setSelectedSize(sz)}
                >
                  {sz}
                </button>
              ))}
            </div>
          </div>

          {/* Delivery Pincode Check */}
          <div className="pincode-box">
            <label>DELIVERY OPTIONS 🚚</label>
            <div className="pincode-input-group">
              <input
                maxLength={6}
                value={pincode}
                onChange={(e) => setPincode(e.target.value)}
                placeholder="Enter Pincode (e.g. 400001)"
              />
              <button onClick={checkDelivery}>Check</button>
            </div>
            {pincodeMsg && <p className="pincode-status">{pincodeMsg}</p>}
          </div>

          {/* CTA Buttons */}
          <div className="modal-cta-buttons">
            <button className="primary-bag-cta" onClick={() => onAddToBag(item, selectedSize)}>
              🛍️ ADD TO BAG
            </button>
            <button
              className={`secondary-wishlist-cta ${isWishlisted ? "active" : ""}`}
              onClick={() => onToggleWishlist(item)}
            >
              {isWishlisted ? "♥ WISHLISTED" : "♡ WISHLIST"}
            </button>
          </div>

          <p className="modal-description">
            {item.description || "A high quality, tailored piece designed for effortless daily elegance and comfort."}
          </p>

          {/* Similar Recommendations Tray */}
          {similarItems.length > 0 && (
            <div className="similar-tray-section">
              <h4>SIMILAR PRODUCTS YOU MAY LIKE</h4>
              <div className="similar-items-row">
                {similarItems.map((sim) => (
                  <div key={sim.article_id} className="similar-mini-card">
                    <ProductImg item={sim} alt={sim.name} height={80} />
                    <span className="sim-title">{sim.name.slice(0, 18)}...</span>
                    <b className="sim-price">{money(priceINR(sim))}</b>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
