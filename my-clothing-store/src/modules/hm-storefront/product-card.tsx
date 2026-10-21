"use client"
import { useImpression } from "./use-impression"
import { useMemo } from "react"
import ProductImg from "./product-img"
import { money, priceINR, type Item, type RecoResult } from "./photos"

interface ProductCardProps {
  item: Item
  result: RecoResult | null
  isWishlisted: boolean
  onSelect: () => void
  onToggleWishlist: (e: React.MouseEvent) => void
  onQuickAdd: (e: React.MouseEvent) => void
  photoSrc?: string
}

export default function ProductCard({
  item,
  result,
  isWishlisted,
  onSelect,
  onToggleWishlist,
  onQuickAdd,
  photoSrc,
}: ProductCardProps) {
  const currentPrice = priceINR(item)
  const impressionRef = useImpression(item, result)

  // Generate deterministic realistic discount % and rating for Myntra style display
  const { originalPrice, discountPct, rating, ratingCount } = useMemo(() => {
    let hash = 0
    for (let i = 0; i < item.article_id.length; i++) {
      hash = (hash << 5) - hash + item.article_id.charCodeAt(i)
      hash |= 0
    }
    const absHash = Math.abs(hash)
    const discountPct = 20 + (absHash % 45) // 20% to 65% OFF
    const originalPrice = Math.round(currentPrice / (1 - discountPct / 100))
    const rating = (3.8 + (absHash % 12) / 10).toFixed(1)
    const ratingCount = `${(0.5 + (absHash % 90) / 10).toFixed(1)}k`
    return { originalPrice, discountPct, rating, ratingCount }
  }, [item.article_id, currentPrice])

  return (
    <article ref={impressionRef} className="myntra-card" onClick={onSelect}>
      <div className="card-image-wrapper">
        <ProductImg item={item} alt={`${item.name} - ${item.colour_group}`} src={photoSrc} />
        
        {/* Myntra Signature Rating Badge */}
        <div className="myntra-rating-badge">
          <span>{rating} ★</span>
          <span className="rating-divider">|</span>
          <span className="rating-count">{ratingCount}</span>
        </div>

        {/* Wishlist Heart Toggle */}
        <button
          className={`wishlist-heart-btn ${isWishlisted ? "active" : ""}`}
          onClick={onToggleWishlist}
          aria-label="Add to wishlist"
          title={isWishlisted ? "Remove from wishlist" : "Save to wishlist"}
        >
          {isWishlisted ? "♥" : "♡"}
        </button>

        {/* Quick Add overlay button */}
        <button className="quick-add-overlay" onClick={onQuickAdd}>
          + Quick Add
        </button>
      </div>

      <div className="card-details">
        <div className="brand-label">H&amp;M EDITION</div>
        <h3 className="product-title" title={item.name}>
          {item.name}
        </h3>
        <p className="product-dept">
          {item.product_type} · {item.colour_group}
        </p>

        <div className="price-row">
          <span className="current-price">{money(currentPrice)}</span>
          <span className="original-price">{money(originalPrice)}</span>
          <span className="discount-badge">{discountPct}% OFF</span>
        </div>
      </div>
    </article>
  )
}

