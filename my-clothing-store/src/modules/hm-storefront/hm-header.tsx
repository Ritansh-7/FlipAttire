"use client"

export default function HmHeader({
  activeCategory,
  bagCount,
  wishlistCount = 0,
  customerShort,
  onBag,
  onWishlist,
  query,
  setQuery,
  onSelectNavCategory,
  showSearch = true,
}: {
  activeCategory?: string
  bagCount: number
  wishlistCount?: number
  customerShort: string
  onBag: () => void
  onWishlist?: () => void
  query?: string
  setQuery?: (value: string) => void
  onSelectNavCategory?: (cat: string) => void
  showSearch?: boolean
}) {
  const handleNavClick = (cat: string) => {
    if (onSelectNavCategory) {
      onSelectNavCategory(cat)
    }
  }

  return (
    <header className="hm-header">
      <div className="hm-header-left">
        <a className="hm-logo" href="/in">
          FlipAttire <span className="logo-sub">STYLE LAB</span>
        </a>
        <nav className="hm-nav-main">
          {["ALL", "WOMEN", "MEN", "KIDS", "BEAUTY", "STUDIO 2026", "SALE"].map((cat) => (
            <a
              key={cat}
              href="#edit"
              className={`nav-link ${activeCategory === cat ? "active" : ""} ${cat === "SALE" ? "sale-link" : ""}`}
              onClick={() => handleNavClick(cat)}
            >
              {cat}
            </a>
          ))}
        </nav>
      </div>

      <div className="hm-header-center">
        {showSearch && setQuery !== undefined && (
          <div className="hm-search-wrapper">
            <span className="search-icon">🔍</span>
            <input
              value={query || ""}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search for tops, dresses, jeans, shoes..."
              aria-label="Search clothing catalog"
              className="hm-search-input"
            />
            {query && (
              <button onClick={() => setQuery("")} className="clear-search" aria-label="Clear search">
                ✕
              </button>
            )}
          </div>
        )}
      </div>

      <div className="hm-header-right">
        <button
          className="hm-action-btn user-btn"
          onClick={() => { window.location.href = "/in/profile" }}
          title="Login / Account — sign in with your ID and password"
        >
          <span className="action-icon">👤</span>
          <span className="action-label">{customerShort}</span>
        </button>

        {onWishlist && (
          <button className="hm-action-btn wishlist-btn" onClick={onWishlist} aria-label="Open wishlist">
            <span className="action-icon">♡</span>
            <span className="action-label">Wishlist</span>
            {wishlistCount > 0 && <span className="badge wishlist-badge">{wishlistCount}</span>}
          </button>
        )}

        <button className="hm-action-btn bag-btn" onClick={onBag} aria-label="Open shopping bag">
          <span className="action-icon">🛍️</span>
          <span className="action-label">Bag</span>
          {bagCount > 0 && <span className="badge bag-badge">{bagCount}</span>}
        </button>
      </div>
    </header>
  )
}
