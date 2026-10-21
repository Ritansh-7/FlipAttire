"use client"

import { useState } from "react"
import { DEFAULT_CUSTOMER, setCustomerIdStored } from "./session"

const SAMPLE_CUSTOMERS = [
  { id: DEFAULT_CUSTOMER, label: "Default Shopper (Fashion Enthusiast)" },
  { id: "000058a17d5c4f3e098a54d43e260b07fd088b93575a3500a8317358b292c48b", label: "Shopper A (Denim & Tops)" },
  { id: "00007d29226d9288518b61252774244c034d1e0d7f9b008d2041d4638d270385", label: "Shopper B (Dresses & Formal)" },
  { id: "00002f8b1d4e6a0938475621abcdef0938475621abcdef0938475621abcd1234", label: "Shopper C (Casual & Activewear)" },
]

export default function CustomerModal({
  currentId,
  onClose,
  onSelectCustomer,
}: {
  currentId: string
  onClose: () => void
  onSelectCustomer: (newId: string) => void
}) {
  const [inputVal, setInputVal] = useState(currentId)

  const handleApply = (idToUse: string) => {
    if (!idToUse.trim()) return
    setCustomerIdStored(idToUse.trim())
    onSelectCustomer(idToUse.trim())
    onClose()
  }

  return (
    <div className="hm-overlay" onClick={onClose}>
      <aside className="hm-drawer" onClick={(e) => e.stopPropagation()}>
        <button onClick={onClose} className="hm-close" aria-label="Close">
          ×
        </button>

        <div className="drawer-header">
          <h2>Switch Profile</h2>
          <p className="drawer-subtitle">Every customer ID has unique history — recommendations follow the active profile.</p>
        </div>

        <div className="preset-card active" style={{ cursor: "default", marginBottom: 16 }}>
          <b>Active profile</b>
          <code style={{ wordBreak: "break-all", fontSize: 11 }}>{currentId}</code>
        </div>

        <div className="preset-customers">
          <h4>Paste a customer ID:</h4>
          <div className="pincode-input-group" style={{ maxWidth: "100%" }}>
            <input
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              placeholder="Paste customer ID hex string..."
            />
            <button onClick={() => handleApply(inputVal)}>Apply</button>
          </div>
        </div>

        <div className="preset-customers">
          <h4>Or pick a sample persona:</h4>
          <div className="preset-list">
            {SAMPLE_CUSTOMERS.map((sample) => (
              <div
                key={sample.id}
                className={`preset-card ${currentId === sample.id ? "active" : ""}`}
                onClick={() => handleApply(sample.id)}
              >
                <b>{sample.label}</b>
                <code>{sample.id.slice(0, 24)}...</code>
              </div>
            ))}
          </div>
        </div>
      </aside>
    </div>
  )
}
