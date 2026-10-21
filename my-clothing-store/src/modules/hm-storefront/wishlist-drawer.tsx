"use client"

import ProductImg from "./product-img"
import { money, priceINR, type Item } from "./photos"

export default function WishlistDrawer({
  wishlist,
  onClose,
  onMoveToBag,
  onRemove,
}: {
  wishlist: Item[]
  onClose: () => void
  onMoveToBag: (item: Item) => void
  onRemove: (articleId: string) => void
}) {
  return (
    <div className="hm-overlay" onClick={onClose}>
      <aside className="hm-drawer wishlist-drawer-card" onClick={(e) => e.stopPropagation()}>
        <button onClick={onClose} className="hm-close" aria-label="Close wishlist">
          ×
        </button>

        <div className="drawer-header">
          <h2>My Wishlist ({wishlist.length})</h2>
          <p className="drawer-subtitle">Your saved pieces · Click to add directly to bag</p>
        </div>

        {wishlist.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">♡</div>
            <p>Your wishlist is empty.</p>
            <span className="empty-caption">Explore the edit and tap the heart icon to save your favourites.</span>
          </div>
        ) : (
          <div className="wishlist-grid">
            {wishlist.map((item) => {
              const p = priceINR(item)
              return (
                <div key={item.article_id} className="wishlist-item-card">
                  <div className="wishlist-img-box">
                    <ProductImg item={item} alt={item.name} height={120} />
                    <button className="remove-wishlist-btn" onClick={() => onRemove(item.article_id)} title="Remove">
                      ✕
                    </button>
                  </div>
                  <div className="wishlist-info">
                    <h4>{item.name}</h4>
                    <p>{item.product_type} · {item.colour_group}</p>
                    <b className="price-tag">{money(p)}</b>
                    <button className="move-to-bag-btn" onClick={() => onMoveToBag(item)}>
                      Move to Bag
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </aside>
    </div>
  )
}
